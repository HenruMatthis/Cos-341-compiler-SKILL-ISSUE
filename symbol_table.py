# symbol_table.py
"""
Symbol table implementation for SPL (COS341 project).
- Static scoping via stack-of-dictionaries.
- Stores detailed info per name for semantic checks and IR renaming.

API highlights:
    st = SymbolTable()
    st.enter_scope(kind="Global", node=program_node)
    st.declare_var(name, node=var_node)           # default numeric
    st.declare_proc(name, node=proc_node)
    st.declare_func(name, node=func_node)
    st.lookup(name) -> SymbolInfo or raise LookupError
    st.exit_scope()
    st.get_unique_name(name)  # mapping original -> internal (v1, v2,...)
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


class SymbolTableError(Exception):
    pass


@dataclass
class SymbolInfo:
    name: str                 # original name in source
    kind: str                 # 'var' | 'proc' | 'func' | 'param'
    decl_type: Optional[str]  # 'numeric' | 'boolean' | 'string' | None for type-less
    scope_level: int          # 0 = Everywhere, 1 = Global, 2+ nested
    unique_name: str          # internal name used by IR (vx, etc.)
    node_id: int              # foreign key to AST node (id(node) or explicit node.node_id)
    extra: Dict[str, Any] = None  # optional storage for other metadata


class SymbolTable:
    def __init__(self, base_unique_prefix: str = "v"):
        # stack of scope dicts; each dict: name -> SymbolInfo
        self._scopes: List[Dict[str, SymbolInfo]] = []
        # metadata about scopes (for debugging): (scope_kind, node_id)
        self._scope_meta: List[Tuple[str, int]] = []
        # global mapping original_name -> next counter (for unique names)
        self._name_counters: Dict[str, int] = {}
        # global list of all declared procs/funcs (useful for cross-checks)
        self._global_procs: Dict[str, SymbolInfo] = {}
        self._global_funcs: Dict[str, SymbolInfo] = {}
        self._unique_prefix = base_unique_prefix

        # start with empty "Everywhere" scope? We'll let caller explicitly push scopes.
        # But we can prepare an empty top-level container:
        # self.enter_scope("Everywhere", node=None)

    # ---------- scope management ----------
    def enter_scope(self, scope_kind: str, node: Optional[Any] = None) -> None:
        """
        Push a new scope.
        scope_kind: friendly name (e.g., 'Everywhere', 'Global', 'Procedure', 'Function', 'Main', 'Local')
        node: AST node for which this scope is created (optional). We'll use id(node) as foreign key.
        """
        node_id = id(node) if node is not None else 0
        self._scopes.append({})
        self._scope_meta.append((scope_kind, node_id))

    def exit_scope(self) -> None:
        """Pop the current scope. If no scope exists, raise."""
        if not self._scopes:
            raise SymbolTableError("Cannot exit scope: no scope on stack")
        popped = self._scopes.pop()
        self._scope_meta.pop()
        # Note: entries removed are gone; spec assumes scopes not needed after exit.

    def current_scope_level(self) -> int:
        """Return current depth (0 means no scopes pushed, 1 = first scope)."""
        return len(self._scopes)

    def current_scope_name(self) -> Optional[str]:
        return self._scope_meta[-1][0] if self._scope_meta else None

    # ---------- unique-name generation ----------
    def _gen_unique_name(self, base_name: str) -> str:
        c = self._name_counters.get(base_name, 0) + 1
        self._name_counters[base_name] = c
        return f"{self._unique_prefix}_{base_name}_{c}"

    # ---------- declarations ----------
    def _declare(self, name: str, kind: str, decl_type: Optional[str], node: Any) -> SymbolInfo:
        if not self._scopes:
            raise SymbolTableError("No scope to declare into; call enter_scope() first")
        # check duplicate in current scope
        curr = self._scopes[-1]
        if name in curr:
            raise SymbolTableError(f"Duplicate declaration of '{name}' in the same scope")
        scope_level = len(self._scopes)
        node_id = getattr(node, "node_id", None) or id(node) if node is not None else 0
        unique_name = self._gen_unique_name(name)
        info = SymbolInfo(name=name, kind=kind, decl_type=decl_type,
                          scope_level=scope_level, unique_name=unique_name,
                          node_id=node_id, extra={})
        curr[name] = info

        # if declared at global (scope_level == 1) and kind is proc/func, track globally
        if scope_level == 1 and kind == "proc":
            self._global_procs[name] = info
        if scope_level == 1 and kind == "func":
            self._global_funcs[name] = info

        return info

    def declare_var(self, name: str, node: Any = None, decl_type: str = "numeric") -> SymbolInfo:
        """Declare a variable (default numeric). Enforce name not used by func/proc in Everywhere scope
           (the check for 'Inside the Everywhere scope, NO variable name may be identical with any function name' etc.)
           should ideally be called after global procs/funcs are known. You may call additional checks after building global lists.
        """
        return self._declare(name, kind="var", decl_type=decl_type, node=node)

    def declare_param(self, name: str, node: Any = None, decl_type: str = "numeric") -> SymbolInfo:
        return self._declare(name, kind="param", decl_type=decl_type, node=node)

    def declare_proc(self, name: str, node: Any = None) -> SymbolInfo:
        # procs are type-less
        return self._declare(name, kind="proc", decl_type=None, node=node)

    def declare_func(self, name: str, node: Any = None) -> SymbolInfo:
        # funcs are type-less in symbol table but must return numeric per spec (checked later)
        return self._declare(name, kind="func", decl_type=None, node=node)

    # ---------- lookup ----------
    def lookup(self, name: str) -> Optional[SymbolInfo]:
        """Lookup (inner->outer). Return SymbolInfo or None."""
        for scope in reversed(self._scopes):
            if name in scope:
                return scope[name]
        return None

    def assert_exists(self, name: str) -> SymbolInfo:
        info = self.lookup(name)
        if info is None:
            raise SymbolTableError(f"Name '{name}' not declared in any visible scope")
        return info

    # ---------- specialized checks ----------
    def check_no_global_name_clashes(self) -> None:
        """
        Enforce:
        - No variable name may be identical with any function name
        - No variable name may be identical with any procedure name
        - No function name may be identical with any procedure name
        The 'Everywhere' (spec text) means check within global-level declarations (scope level 1).
        """
        # gather all names declared in global scope (scope level 1)
        if len(self._scopes) < 1:
            return
        global_scope = self._scopes[0] if len(self._scopes) >= 1 else {}

        # find all kinds
        vars_ = {n for n, si in global_scope.items() if si.kind == "var"}
        procs_ = {n for n, si in global_scope.items() if si.kind == "proc"}
        funcs_ = {n for n, si in global_scope.items() if si.kind == "func"}
        
        # check intersections
        clashes = []
        if vars_ & funcs_:
            clashes.append(f"Variable/function name clash: {vars_ & funcs_}")
        if vars_ & procs_:
            clashes.append(f"Variable/procedure name clash: {vars_ & procs_}")
        if funcs_ & procs_:
            clashes.append(f"Function/procedure name clash: {funcs_ & procs_}")
        if clashes:
            raise SymbolTableError("; ".join(clashes))

    def check_no_shadowing_of_params(self, param_names: List[str], local_names: List[str]) -> None:
        """
        Called while checking a particular function/procedure body:
        ensure no local variable shadows parameter names.
        """
        shadow = set(param_names) & set(local_names)
        if shadow:
            raise SymbolTableError(f"Shadowing of parameters not allowed: {shadow}")

    # ---------- utility ----------
    def get_scope_snapshot(self) -> List[Dict[str, SymbolInfo]]:
        """Return shallow copy of scopes for inspection / tests."""
        return [dict(s) for s in self._scopes]

    def find_symbol_by_node(self, node: Any) -> Optional[SymbolInfo]:
        """Return symbol info whose node_id matches id(node) or node.node_id if present."""
        search_id = getattr(node, "node_id", None) or id(node)
        for scope in self._scopes:
            for si in scope.values():
                if si.node_id == search_id:
                    return si
        return None

    def __repr__(self):
        lines = []
        for i, sc in enumerate(self._scopes, start=1):
            meta = self._scope_meta[i-1] if i-1 < len(self._scope_meta) else ("<unknown>", 0)
            lines.append(f"Scope {i} ({meta[0]}, node_id={meta[1]}):")
            for name, info in sc.items():
                lines.append(f"  {name} -> {info}")
        return "\n".join(lines)
