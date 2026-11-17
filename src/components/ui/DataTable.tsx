import { useRef, useCallback } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import {
  ArrowDown,
  ArrowUp,
  ChevronLeft,
  ChevronRight,
  ChevronsUpDown,
  Columns3,
  Download,
  FilterX,
  Inbox } from
'lucide-react';
import { cn } from '../../utils/cn';
import { downloadCsv } from '../../utils/export';
import {
  useDataTable,
  type Column,
  type TableFilter } from
'../../hooks/useDataTable';
import { Button } from './Button';
import { Checkbox } from './Controls';
import { Dropdown, DropdownItem, DropdownLabel } from './Dropdown';
import { SearchInput } from './Input';
import { SkeletonTable } from './Skeleton';
import { EmptyState, ErrorState } from './States';
import { Tooltip } from './Tooltip';

export type { Column, TableFilter };

export interface DataTableProps<T> {
  columns: Column<T>[];
  rows: T[];
  getRowId: (row: T) => string;
  filters?: TableFilter<T>[];
  pageSize?: number;
  loading?: boolean;
  error?: boolean;
  onRetry?: () => void;
  onRowClick?: (row: T) => void;
  searchPlaceholder?: string;
  exportName?: string;
  bulkActions?: (selectedRows: T[], clear: () => void) => React.ReactNode;
  toolbarExtra?: React.ReactNode;
  emptyTitle?: string;
  emptyDescription?: string;
  emptyAction?: React.ReactNode;
  className?: string;
  ariaLabel: string;
}

export function DataTable<T>({
  columns,
  rows,
  getRowId,
  filters = [],
  pageSize = 8,
  loading = false,
  error = false,
  onRetry,
  onRowClick,
  searchPlaceholder = 'Search...',
  exportName = 'sentinel-export',
  bulkActions,
  toolbarExtra,
  emptyTitle = 'No results',
  emptyDescription = 'Nothing matches the current search and filters. Adjust them to widen the result set.',
  emptyAction,
  className,
  ariaLabel
}: DataTableProps<T>) {
  const table = useDataTable<T>({ rows, columns, filters, pageSize });
  const resizing = useRef<{id: string;startX: number;startWidth: number;} | null>(null);

  const onResizeStart = useCallback(
    (event: React.MouseEvent, column: Column<T>) => {
      event.preventDefault();
      event.stopPropagation();
      const startWidth = table.widths[column.id] ?? column.width ?? 180;
      resizing.current = { id: column.id, startX: event.clientX, startWidth };

      const onMove = (e: MouseEvent) => {
        if (!resizing.current) return;
        const delta = e.clientX - resizing.current.startX;
        table.setWidth(
          resizing.current.id,
          Math.max(column.minWidth ?? 96, resizing.current.startWidth + delta)
        );
      };
      const onUp = () => {
        resizing.current = null;
        document.removeEventListener('mousemove', onMove);
        document.removeEventListener('mouseup', onUp);
        document.body.style.cursor = '';
      };
      document.body.style.cursor = 'col-resize';
      document.addEventListener('mousemove', onMove);
      document.addEventListener('mouseup', onUp);
    },
    [table]
  );

  const selectedRows = table.allRows.filter((_, i) => table.selected.has(i));

  const handleExport = () => {
    downloadCsv(
      exportName,
      table.visibleColumns.map((c) => c.header),
      table.allRows.map((row) => table.visibleColumns.map((c) => c.accessor(row)))
    );
  };

  return (
    <div
      className={cn(
        'overflow-hidden rounded-xl border border-border bg-card shadow-xs',
        className
      )}>
      
      {/* Toolbar */}
      <div className="flex flex-col gap-3 border-b border-border px-4 py-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex flex-1 flex-wrap items-center gap-2">
          <SearchInput
            value={table.query}
            onChange={(e) => table.setQuery(e.target.value)}
            placeholder={searchPlaceholder}
            aria-label={`Search ${ariaLabel}`}
            wrapperClassName="w-full sm:w-64" />
          
          {filters.map((filter) =>
          <FilterChip
            key={filter.id}
            filter={filter}
            value={table.filterValues[filter.id] ?? 'all'}
            onChange={(v) => table.setFilter(filter.id, v)} />

          )}
          {table.activeFilterCount > 0 &&
          <Button
            variant="ghost"
            size="sm"
            onClick={table.reset}
            iconLeft={<FilterX className="h-3.5 w-3.5" />}>
            
              Clear
            </Button>
          }
        </div>
        <div className="flex items-center gap-2">
          {toolbarExtra}
          <Dropdown
            label="Toggle columns"
            trigger={({ toggle }) =>
            <Tooltip label="Column visibility">
                <Button
                variant="outline"
                size="sm"
                onClick={toggle}
                iconLeft={<Columns3 className="h-3.5 w-3.5" />}>
                
                  Columns
                </Button>
              </Tooltip>
            }>
            
            <DropdownLabel>Visible columns</DropdownLabel>
            {columns.
            filter((c) => c.hideable !== false).
            map((c) =>
            <DropdownItem
              key={c.id}
              selected={!table.hidden.has(c.id)}
              onClick={() => table.toggleColumn(c.id)}>
              
                  {c.header}
                </DropdownItem>
            )}
          </Dropdown>
          <Tooltip label="Export visible rows as CSV">
            <Button
              variant="outline"
              size="sm"
              onClick={handleExport}
              iconLeft={<Download className="h-3.5 w-3.5" />}>
              
              Export
            </Button>
          </Tooltip>
        </div>
      </div>

      {/* Bulk action bar */}
      <AnimatePresence initial={false}>
        {bulkActions && table.selected.size > 0 &&
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}
          className="overflow-hidden border-b border-primary/25 bg-primary/[0.06]">
          
            <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-2.5">
              <p className="text-xs font-medium text-primary">
                {table.selected.size} selected
              </p>
              <div className="flex items-center gap-2">
                {bulkActions(selectedRows, table.clearSelection)}
                <Button variant="ghost" size="sm" onClick={table.clearSelection}>
                  Deselect
                </Button>
              </div>
            </div>
          </motion.div>
        }
      </AnimatePresence>

      {/* Table */}
      {error ?
      <ErrorState className="m-4 border-0" onRetry={onRetry} /> :
      loading ?
      <SkeletonTable rows={pageSize} cols={Math.min(6, table.visibleColumns.length + 1)} /> :
      table.total === 0 ?
      <EmptyState
        icon={<Inbox className="h-6 w-6" />}
        title={emptyTitle}
        description={emptyDescription}
        action={emptyAction}
        secondaryAction={
        table.activeFilterCount > 0 ?
        <Button variant="outline" size="sm" onClick={table.reset}>
                Reset filters
              </Button> :
        undefined
        } /> :


      <div className="relative max-h-[620px] overflow-auto">
          <table
          className="w-full border-collapse text-left text-sm"
          aria-label={ariaLabel}>
          
            <thead className="sticky top-0 z-20">
              <tr className="bg-surface-2/95 backdrop-blur supports-[backdrop-filter]:bg-surface-2/80">
                {bulkActions &&
              <th
                scope="col"
                className="sticky left-0 z-30 w-10 border-b border-border bg-surface-2/95 px-4 py-2.5">
                
                    <Checkbox
                  label="Select all rows"
                  checked={
                  table.selected.size === table.allRows.length &&
                  table.allRows.length > 0
                  }
                  indeterminate={
                  table.selected.size > 0 &&
                  table.selected.size < table.allRows.length
                  }
                  onChange={table.toggleSelectAll} />
                
                  </th>
              }
                {table.visibleColumns.map((column) => {
                const active = table.sort?.id === column.id;
                return (
                  <th
                    key={column.id}
                    scope="col"
                    aria-sort={
                    active ?
                    table.sort?.dir === 'asc' ?
                    'ascending' :
                    'descending' :
                    'none'
                    }
                    style={{ width: table.widths[column.id] ?? column.width }}
                    className={cn(
                      'group relative border-b border-border px-4 py-2.5 text-2xs font-semibold uppercase tracking-wider text-muted-foreground',
                      column.align === 'right' && 'text-right',
                      column.sticky &&
                      'sticky left-0 z-30 bg-surface-2/95 lg:shadow-[1px_0_0_0_var(--border)]'
                    )}>
                    
                      {column.sortable === false ?
                    column.header :

                    <button
                      type="button"
                      onClick={() => table.toggleSort(column.id)}
                      className={cn(
                        'inline-flex items-center gap-1.5 rounded transition-colors duration-150 hover:text-foreground',
                        active && 'text-foreground'
                      )}>
                      
                          {column.header}
                          {active ?
                      table.sort?.dir === 'asc' ?
                      <ArrowUp className="h-3 w-3" aria-hidden /> :

                      <ArrowDown className="h-3 w-3" aria-hidden /> :


                      <ChevronsUpDown
                        className="h-3 w-3 opacity-0 transition-opacity group-hover:opacity-60"
                        aria-hidden />

                      }
                        </button>
                    }
                      <span
                      role="separator"
                      aria-orientation="vertical"
                      onMouseDown={(e) => onResizeStart(e, column)}
                      className="absolute right-0 top-0 h-full w-1.5 cursor-col-resize opacity-0 transition-opacity duration-150 hover:opacity-100 group-hover:opacity-60">
                      
                        <span className="absolute right-0.5 top-1/2 h-4 w-px -translate-y-1/2 bg-border-strong" />
                      </span>
                    </th>);

              })}
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {table.rows.map((row, index) => {
              const globalIndex = table.page * table.pageSize + index;
              const isSelected = table.selected.has(globalIndex);
              return (
                <tr
                  key={getRowId(row)}
                  onClick={() => onRowClick?.(row)}
                  tabIndex={onRowClick ? 0 : undefined}
                  onKeyDown={(e) => {
                    if (onRowClick && (e.key === 'Enter' || e.key === ' ')) {
                      e.preventDefault();
                      onRowClick(row);
                    }
                  }}
                  className={cn(
                    'transition-colors duration-150',
                    onRowClick && 'cursor-pointer',
                    isSelected ? 'bg-primary/[0.07]' : 'hover:bg-accent/60',
                    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring/70'
                  )}>
                  
                    {bulkActions &&
                  <td
                    className={cn(
                      'sticky left-0 z-10 w-10 px-4 py-3',
                      isSelected ? 'bg-primary/[0.07]' : 'bg-card'
                    )}
                    onClick={(e) => e.stopPropagation()}>
                    
                        <Checkbox
                      label={`Select row ${getRowId(row)}`}
                      checked={isSelected}
                      onChange={() => table.toggleSelect(globalIndex)} />
                    
                      </td>
                  }
                    {table.visibleColumns.map((column) =>
                  <td
                    key={column.id}
                    className={cn(
                      'px-4 py-3 align-middle text-[13px] text-foreground',
                      column.align === 'right' && 'text-right',
                      column.sticky &&
                      cn(
                        'sticky left-0 z-10',
                        isSelected ? 'bg-primary/[0.07]' : 'bg-card'
                      )
                    )}>
                    
                        {column.cell ? column.cell(row) : column.accessor(row)}
                      </td>
                  )}
                  </tr>);

            })}
            </tbody>
          </table>
        </div>
      }

      {/* Pagination */}
      {!loading && !error && table.total > 0 &&
      <div className="flex flex-col gap-3 border-t border-border px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs text-muted-foreground">
            Showing{' '}
            <span className="font-medium text-foreground">
              {table.page * table.pageSize + 1}”“
              {Math.min((table.page + 1) * table.pageSize, table.total)}
            </span>{' '}
            of <span className="font-medium text-foreground">{table.total}</span>
          </p>
          <div className="flex items-center gap-1">
            <Button
            variant="outline"
            size="icon-sm"
            aria-label="Previous page"
            disabled={table.page === 0}
            onClick={() => table.setPage(table.page - 1)}>
            
              <ChevronLeft className="h-4 w-4" />
            </Button>
            {Array.from({ length: table.pageCount }).
          slice(0, 7).
          map((_, i) =>
          <button
            key={i}
            type="button"
            aria-label={`Page ${i + 1}`}
            aria-current={table.page === i ? 'page' : undefined}
            onClick={() => table.setPage(i)}
            className={cn(
              'h-7 min-w-[28px] rounded-md px-2 font-mono text-xs transition-colors duration-150',
              table.page === i ?
              'bg-primary text-primary-foreground' :
              'text-muted-foreground hover:bg-accent hover:text-foreground'
            )}>
            
                  {i + 1}
                </button>
          )}
            <Button
            variant="outline"
            size="icon-sm"
            aria-label="Next page"
            disabled={table.page >= table.pageCount - 1}
            onClick={() => table.setPage(table.page + 1)}>
            
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      }
    </div>);

}

function FilterChip<T>({
  filter,
  value,
  onChange




}: {filter: TableFilter<T>;value: string;onChange: (value: string) => void;}) {
  const active = value !== 'all';
  const current = filter.options.find((o) => o.value === value);
  return (
    <Dropdown
      align="start"
      label={filter.label}
      trigger={({ toggle }) =>
      <Button
        variant={active ? 'secondary' : 'outline'}
        size="sm"
        onClick={toggle}
        className={cn(active && 'border-primary/40 text-primary')}>
        
          {filter.label}
          {active &&
        <span className="ml-1 font-normal opacity-80">· {current?.label}</span>
        }
        </Button>
      }>
      
      {(close) =>
      <>
          <DropdownLabel>{filter.label}</DropdownLabel>
          <DropdownItem
          selected={value === 'all'}
          onClick={() => {
            onChange('all');
            close();
          }}>
          
            All
          </DropdownItem>
          {filter.options.map((option) =>
        <DropdownItem
          key={option.value}
          selected={value === option.value}
          onClick={() => {
            onChange(option.value);
            close();
          }}>
          
              {option.label}
            </DropdownItem>
        )}
        </>
      }
    </Dropdown>);

}