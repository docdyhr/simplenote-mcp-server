# Refactoring Plan - Code Complexity Improvements

**Date**: January 26, 2025  
**Version**: 1.8.1+  
**Status**: 📋 Planning Phase  
**Priority**: Medium

---

## 📊 Current State Analysis

### Complexity Metrics Summary

```
Average Maintainability Index: 57.8 (Good)
Functions with High Complexity (CC >= 15): 28
Functions Above Threshold (CC >= 10): 83
Files with Low Maintainability (MI < 20): 1
```

### Top Complexity Hot Spots

| File | Function | Complexity | Priority |
|------|----------|------------|----------|
| `scripts/analyze_logs.py` | `generate_report` | 38 | Low (Script) |
| `server/cache.py` | `update_cache_after_update` | 33 | **HIGH** |
| `server/search/engine.py` | `search` | 30 | **HIGH** |
| `server/cache.py` | `sync` | 28 | **HIGH** |
| `server/cache.py` | `initialize` | 27 | **HIGH** |
| `server/cache.py` | `search_notes` | 24 | Medium |
| `server/security.py` | `validate_arguments` | 22 | Medium |
| `server/errors.py` | `handle_exception` | 22 | Medium |
| `server/cache.py` | `update_cache_after_delete` | 20 | Medium |

### Critical File: `server/cache.py`

**Maintainability Index**: 12.7 (Low - B Rank)

This file has:
- 5 functions with complexity >= 20
- Multiple responsibilities (storage, sync, search, validation)
- 1,146 lines of code

---

## 🎯 Refactoring Goals

1. **Reduce Complexity**: Bring all functions below CC 15
2. **Improve Maintainability**: Increase MI above 20 for all files
3. **Better Separation of Concerns**: Split large modules
4. **Maintain Test Coverage**: Keep 69%+ coverage during refactoring
5. **Zero Regressions**: All 756 tests must continue passing

---

## 📋 Refactoring Tasks

### Phase 1: Cache Module Refactoring (HIGH Priority)

**Target**: `simplenote_mcp/server/cache.py`

#### 1.1 Extract Cache Storage Layer

**New File**: `simplenote_mcp/server/cache/storage.py`

Move storage-related functionality:
- `_notes` dictionary management
- `_tags` set management
- Index management (`_tag_index`, `_title_index`)
- Query cache management

**Complexity Reduction**: ~200 lines → separate concerns

```python
# New structure
class CacheStorage:
    """Low-level cache storage operations."""
    def __init__(self):
        self._notes: dict[str, dict] = {}
        self._tags: set[str] = set()
        self._tag_index: dict[str, set[str]] = {}
        self._title_index: dict[str, list[str]] = {}
    
    def get_note(self, note_id: str) -> dict | None: ...
    def store_note(self, note: dict) -> None: ...
    def remove_note(self, note_id: str) -> bool: ...
    def get_all_notes(self) -> dict[str, dict]: ...
```

#### 1.2 Extract Cache Synchronization

**New File**: `simplenote_mcp/server/cache/sync.py`

Move sync-related functionality:
- `sync()` method (CC 28 → split into smaller methods)
- Background sync logic
- Sync state management
- API interaction for syncing

**Complexity Reduction**: Break `sync()` into:
- `_fetch_updates()` (CC ~8)
- `_apply_updates()` (CC ~8)
- `_handle_sync_errors()` (CC ~6)
- `_update_sync_state()` (CC ~4)

#### 1.3 Extract Cache Search

**New File**: `simplenote_mcp/server/cache/search.py`

Move search-related functionality:
- `search_notes()` method (CC 24)
- Query cache management
- Search result filtering and sorting

**Complexity Reduction**: Break into:
- `_execute_search_query()` (CC ~8)
- `_filter_results()` (CC ~6)
- `_sort_results()` (CC ~5)
- `_cache_search_results()` (CC ~3)

#### 1.4 Simplify Update Methods

**Target Functions**:
- `update_cache_after_update()` (CC 33 → < 15)
- `update_cache_after_delete()` (CC 20 → < 10)

**Strategy**: Extract validation and index update logic

```python
# BEFORE (CC 33)
def update_cache_after_update(self, note: dict) -> None:
    # 33 branches for validation, indexing, tagging, etc.
    ...

# AFTER (CC ~8)
def update_cache_after_update(self, note: dict) -> None:
    self._validate_note(note)
    self._update_storage(note)
    self._update_indexes(note)
    self._update_tags(note)

def _validate_note(self, note: dict) -> None:  # CC ~5
    ...

def _update_storage(self, note: dict) -> None:  # CC ~3
    ...

def _update_indexes(self, note: dict) -> None:  # CC ~4
    ...

def _update_tags(self, note: dict) -> None:  # CC ~3
    ...
```

#### 1.5 Simplify Initialize Method

**Target**: `initialize()` (CC 27 → < 15)

**Strategy**: Extract retry logic and data processing

```python
# BEFORE (CC 27)
async def initialize(self) -> int:
    # Complex retry logic with multiple branches
    ...

# AFTER (CC ~8)
async def initialize(self) -> int:
    await self._fetch_notes_with_retry()
    self._process_note_data()
    await self._fetch_index_mark()
    return len(self._notes)

async def _fetch_notes_with_retry(self) -> list[dict]:  # CC ~10
    ...

def _process_note_data(self, notes: list[dict]) -> None:  # CC ~5
    ...
```

### Phase 2: Search Engine Refactoring (HIGH Priority)

**Target**: `simplenote_mcp/server/search/engine.py`

#### 2.1 Simplify Main Search Method

**Target**: `search()` (CC 30 → < 15)

**Strategy**: Extract query parsing, filtering, and ranking

```python
# New structure
class SearchEngine:
    def search(self, query: str, notes: list[dict]) -> list[dict]:
        parsed_query = self._parse_query(query)  # CC ~5
        filtered = self._filter_notes(parsed_query, notes)  # CC ~8
        ranked = self._rank_results(filtered, parsed_query)  # CC ~6
        return ranked
```

### Phase 3: Security & Error Handling (Medium Priority)

#### 3.1 Security Validation

**Target**: `server/security.py::validate_arguments()` (CC 22 → < 15)

**Strategy**: Extract validation rules per argument type

```python
# New structure
class ArgumentValidator:
    def validate_arguments(self, args: dict) -> None:  # CC ~5
        for key, value in args.items():
            self._validate_single_argument(key, value)
    
    def _validate_single_argument(self, key: str, value: Any) -> None:  # CC ~8
        validator = self._get_validator(key)
        validator(value)
    
    def _get_validator(self, key: str) -> Callable:  # CC ~3
        ...
```

#### 3.2 Error Handling

**Target**: `server/errors.py::handle_exception()` (CC 22 → < 15)

**Strategy**: Use dictionary dispatch instead of if-elif chains

```python
# New structure
ERROR_HANDLERS = {
    NetworkError: _handle_network_error,
    AuthenticationError: _handle_auth_error,
    ValidationError: _handle_validation_error,
    # ... etc
}

def handle_exception(e: Exception, context: str) -> Exception:
    handler = ERROR_HANDLERS.get(type(e), _handle_generic_error)
    return handler(e, context)
```

---

## 📦 New Module Structure

### Current Structure
```
simplenote_mcp/server/
├── cache.py              (1,146 lines, MI 12.7)
├── search/
│   └── engine.py         (search() CC 30)
├── security.py           (validate_arguments() CC 22)
└── errors.py             (handle_exception() CC 22)
```

### Proposed Structure
```
simplenote_mcp/server/
├── cache/
│   ├── __init__.py       (Public API, main NoteCache class)
│   ├── storage.py        (CacheStorage - low-level operations)
│   ├── sync.py           (CacheSynchronizer - background sync)
│   ├── search.py         (CacheSearch - search operations)
│   └── indexes.py        (IndexManager - tag/title indexes)
├── search/
│   ├── engine.py         (SearchEngine - simplified)
│   ├── query.py          (QueryParser)
│   ├── filters.py        (ResultFilters)
│   └── ranking.py        (ResultRanker)
├── security/
│   ├── __init__.py
│   ├── validators.py     (Argument validators)
│   └── rules.py          (Validation rules)
└── errors/
    ├── __init__.py
    ├── handlers.py       (Error handlers)
    └── taxonomy.py       (Error classification)
```

---

## 🔄 Migration Strategy

### Step 1: Create New Modules (Non-Breaking)

1. Create new module structure
2. Implement new classes
3. Add comprehensive tests for new modules
4. Keep old code intact

**Duration**: 1-2 days  
**Risk**: Low (no existing code changed)

### Step 2: Update Internal References

1. Update `cache.py` to use new modules internally
2. Maintain public API compatibility
3. Run full test suite after each change

**Duration**: 2-3 days  
**Risk**: Medium (requires careful testing)

### Step 3: Update External References

1. Update imports in other modules
2. Update documentation
3. Add deprecation warnings for old imports

**Duration**: 1 day  
**Risk**: Low (tests will catch issues)

### Step 4: Remove Old Code

1. Remove deprecated code
2. Update all references
3. Final test suite run

**Duration**: 1 day  
**Risk**: Low (already tested in steps 2-3)

---

## ✅ Success Criteria

### Code Quality Metrics

- [ ] All functions have CC < 15
- [ ] All files have MI > 20
- [ ] Average MI increases from 57.8 to > 65
- [ ] No functions with CC > 20

### Test Coverage

- [ ] Maintain 69%+ test coverage
- [ ] All 756 existing tests pass
- [ ] Add 50+ tests for new modules
- [ ] Integration tests for refactored code

### Performance

- [ ] No performance regression (< 5% slower)
- [ ] Startup time remains < 1 second
- [ ] Cache operations maintain current speed

### Documentation

- [ ] Update all docstrings
- [ ] Update architecture documentation
- [ ] Add migration guide
- [ ] Update developer documentation

---

## 📅 Timeline

### Week 1: Planning & Setup
- [x] Generate complexity report
- [x] Create refactoring plan
- [ ] Review plan with stakeholders
- [ ] Set up feature branch

### Week 2-3: Phase 1 (Cache Refactoring)
- [ ] Extract storage layer
- [ ] Extract sync layer
- [ ] Extract search layer
- [ ] Simplify update methods
- [ ] Add tests for new modules

### Week 4: Phase 2 (Search Engine)
- [ ] Refactor search engine
- [ ] Add tests
- [ ] Performance benchmarks

### Week 5: Phase 3 (Security & Errors)
- [ ] Refactor security validation
- [ ] Refactor error handling
- [ ] Add tests

### Week 6: Integration & Testing
- [ ] Integration testing
- [ ] Performance testing
- [ ] Documentation updates
- [ ] Code review

### Week 7: Deployment
- [ ] Merge to main
- [ ] Monitor production
- [ ] Address any issues

**Total Duration**: 7 weeks  
**Effort**: ~80-100 hours

---

## 🚧 Risks & Mitigation

### Risk 1: Breaking Changes

**Probability**: Medium  
**Impact**: High

**Mitigation**:
- Maintain backward compatibility
- Comprehensive test coverage
- Gradual migration strategy
- Feature flags for new code

### Risk 2: Performance Regression

**Probability**: Low  
**Impact**: High

**Mitigation**:
- Benchmark before/after
- Profile hot paths
- Performance tests in CI
- Rollback plan ready

### Risk 3: Test Coverage Drop

**Probability**: Low  
**Impact**: Medium

**Mitigation**:
- Write tests first (TDD approach)
- Monitor coverage in CI
- Require > 70% coverage for new code
- Don't remove tests during refactoring

### Risk 4: Scope Creep

**Probability**: Medium  
**Impact**: Medium

**Mitigation**:
- Stick to plan
- Prioritize high-complexity items
- Time-box each phase
- Defer non-critical improvements

---

## 📊 Expected Outcomes

### Complexity Improvements

| Metric | Before | Target | Improvement |
|--------|--------|--------|-------------|
| Functions CC >= 15 | 28 | < 5 | 82% reduction |
| Functions CC >= 10 | 83 | < 30 | 64% reduction |
| Average MI | 57.8 | > 65 | 12% increase |
| Files MI < 20 | 1 | 0 | 100% resolution |

### Code Quality Benefits

- **Better Maintainability**: Easier to understand and modify
- **Lower Bug Risk**: Simpler code = fewer bugs
- **Faster Onboarding**: New developers can understand code faster
- **Better Testing**: Smaller functions are easier to test
- **Clearer Architecture**: Separation of concerns improves design

### Team Benefits

- **Easier Code Reviews**: Smaller, focused changes
- **Faster Development**: Less time debugging complex code
- **Better Collaboration**: Clear module boundaries
- **Reduced Technical Debt**: Proactive improvement

---

## 🔗 Related Documents

- `complexity-report.json` - Detailed complexity metrics
- `TECHNICAL_DEBT_REPORT.md` - Overall technical debt analysis
- `PROJECT_IMPROVEMENTS_SUMMARY_2025_01.md` - Recent improvements
- `CONTRIBUTING.md` - Development guidelines

---

## 📝 Notes

### Why Not Refactor Now?

This is a **medium priority** task because:

1. **Current code works well**: 756 tests passing, zero diagnostics
2. **Recent critical fix**: Just resolved Claude Desktop timeout
3. **Production stability**: Don't want to introduce risk unnecessarily
4. **Resource availability**: Requires dedicated time from maintainer

### When to Start?

**Recommended timing**:
- After current version (1.8.1+) is stable in production
- When maintainer has 2-3 weeks of dedicated time
- After user feedback is collected
- Before adding major new features

### Alternative Approach

If full refactoring is too much:

**Incremental Refactoring**:
- Fix one high-complexity function per release
- Target: Reduce CC by 5 points per function
- Timeline: 6 months vs 7 weeks
- Lower risk, slower progress

---

**Status**: ⏸️ **Planned - Not Started**  
**Next Action**: Review plan and decide on timing  
**Owner**: Project Maintainer  
**Last Updated**: January 26, 2025
