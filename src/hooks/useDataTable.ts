import { useCallback, useMemo, useState, type ReactNode } from 'react';

export interface Column<T> {
  id: string;
  header: string;
  /** Value used for sorting, searching and CSV export. */
  accessor: (row: T) => string | number;
  cell?: (row: T) => ReactNode;
  width?: number;
  minWidth?: number;
  align?: 'left' | 'right';
  sortable?: boolean;
  sticky?: boolean;
  hideable?: boolean;
}

export interface TableFilter<T> {
  id: string;
  label: string;
  options: {value: string;label: string;}[];
  predicate: (row: T, value: string) => boolean;
}

export type SortState = {id: string;dir: 'asc' | 'desc';} | null;

export function useDataTable<T>({
  rows,
  columns,
  filters = [],
  pageSize = 8,
  initialSort = null






}: {rows: T[];columns: Column<T>[];filters?: TableFilter<T>[];pageSize?: number;initialSort?: SortState;}) {
  const [query, setQuery] = useState('');
  const [sort, setSort] = useState<SortState>(initialSort);
  const [page, setPage] = useState(0);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [filterValues, setFilterValues] = useState<Record<string, string>>({});
  const [hidden, setHidden] = useState<Set<string>>(new Set());
  const [widths, setWidths] = useState<Record<string, number>>({});

  const visibleColumns = useMemo(
    () => columns.filter((c) => !hidden.has(c.id)),
    [columns, hidden]
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return rows.filter((row) => {
      const matchesQuery =
      q.length === 0 ||
      columns.some((c) => String(c.accessor(row)).toLowerCase().includes(q));
      if (!matchesQuery) return false;
      return filters.every((f) => {
        const value = filterValues[f.id];
        if (!value || value === 'all') return true;
        return f.predicate(row, value);
      });
    });
  }, [rows, columns, query, filters, filterValues]);

  const sorted = useMemo(() => {
    if (!sort) return filtered;
    const column = columns.find((c) => c.id === sort.id);
    if (!column) return filtered;
    return [...filtered].sort((a, b) => {
      const av = column.accessor(a);
      const bv = column.accessor(b);
      const cmp =
      typeof av === 'number' && typeof bv === 'number' ?
      av - bv :
      String(av).localeCompare(String(bv));
      return sort.dir === 'asc' ? cmp : -cmp;
    });
  }, [filtered, sort, columns]);

  const pageCount = Math.max(1, Math.ceil(sorted.length / pageSize));
  const safePage = Math.min(page, pageCount - 1);
  const paged = useMemo(
    () => sorted.slice(safePage * pageSize, safePage * pageSize + pageSize),
    [sorted, safePage, pageSize]
  );

  const toggleSort = useCallback((id: string) => {
    setSort((current) => {
      if (!current || current.id !== id) return { id, dir: 'asc' };
      if (current.dir === 'asc') return { id, dir: 'desc' };
      return null;
    });
    setPage(0);
  }, []);

  const toggleSelect = useCallback((index: number) => {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(index)) next.delete(index);else
      next.add(index);
      return next;
    });
  }, []);

  const toggleSelectAll = useCallback(() => {
    setSelected((current) =>
    current.size === sorted.length ? new Set() : new Set(sorted.map((_, i) => i))
    );
  }, [sorted.length]);

  const toggleColumn = useCallback((id: string) => {
    setHidden((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);else
      next.add(id);
      return next;
    });
  }, []);

  const setWidth = useCallback((id: string, width: number) => {
    setWidths((current) => ({ ...current, [id]: width }));
  }, []);

  const setFilter = useCallback((id: string, value: string) => {
    setFilterValues((current) => ({ ...current, [id]: value }));
    setPage(0);
  }, []);

  const reset = useCallback(() => {
    setQuery('');
    setFilterValues({});
    setSort(initialSort);
    setPage(0);
  }, [initialSort]);

  const activeFilterCount =
  Object.values(filterValues).filter((v) => v && v !== 'all').length + (
  query.trim() ? 1 : 0);

  return {
    query,
    setQuery: (value: string) => {
      setQuery(value);
      setPage(0);
    },
    sort,
    toggleSort,
    page: safePage,
    setPage,
    pageCount,
    pageSize,
    rows: paged,
    total: sorted.length,
    allRows: sorted,
    selected,
    toggleSelect,
    toggleSelectAll,
    clearSelection: () => setSelected(new Set()),
    filterValues,
    setFilter,
    hidden,
    toggleColumn,
    visibleColumns,
    widths,
    setWidth,
    reset,
    activeFilterCount
  };
}