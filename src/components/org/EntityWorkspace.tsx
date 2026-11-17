import { useState } from 'react';
import { PageHeader } from '../layout/PageHeader';
import { DataTable, type Column, type TableFilter } from '../ui/DataTable';
import { Drawer } from '../ui/Drawer';
import { Button } from '../ui/Button';

/**
 * One reusable asset-explorer architecture reused by every organization,
 * governance and assurance workspace: header â†’ optional metric strip â†’
 * filterable table â†’ detail drawer.
 */
export function EntityWorkspace<T>({
  eyebrow,
  title,
  subtitle,
  meta,
  actions,
  metrics,
  beforeTable,
  aside,
  columns,
  rows,
  getRowId,
  filters,
  pageSize = 8,
  searchPlaceholder,
  exportName,
  ariaLabel,
  bulkActions,
  detail
























}: {eyebrow?: React.ReactNode;title: string;subtitle: string;meta?: React.ReactNode;actions?: React.ReactNode;metrics?: React.ReactNode;beforeTable?: React.ReactNode;aside?: React.ReactNode;columns: Column<T>[];rows: T[];getRowId: (row: T) => string;filters?: TableFilter<T>[];pageSize?: number;searchPlaceholder?: string;exportName: string;ariaLabel: string;bulkActions?: (selected: T[], clear: () => void) => React.ReactNode;detail?: {title: (row: T) => string;subtitle?: (row: T) => string;eyebrow?: (row: T) => React.ReactNode;render: (row: T) => React.ReactNode;actions?: (row: T) => React.ReactNode;};}) {
  const [active, setActive] = useState<T | null>(null);

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow={eyebrow}
        title={title}
        subtitle={subtitle}
        meta={meta}
        actions={actions} />
      

      {metrics}

      {beforeTable}

      {aside ?
      <div className="grid gap-4 xl:grid-cols-3">
          <div className="xl:col-span-2">
            <DataTable<T>
            ariaLabel={ariaLabel}
            columns={columns}
            rows={rows}
            getRowId={getRowId}
            filters={filters}
            pageSize={pageSize}
            exportName={exportName}
            searchPlaceholder={searchPlaceholder}
            onRowClick={detail ? setActive : undefined}
            bulkActions={bulkActions} />
          
          </div>
          <div className="space-y-4">{aside}</div>
        </div> :

      <DataTable<T>
        ariaLabel={ariaLabel}
        columns={columns}
        rows={rows}
        getRowId={getRowId}
        filters={filters}
        pageSize={pageSize}
        exportName={exportName}
        searchPlaceholder={searchPlaceholder}
        onRowClick={detail ? setActive : undefined}
        bulkActions={bulkActions} />

      }

      {detail &&
      <Drawer
        open={Boolean(active)}
        onClose={() => setActive(null)}
        width="lg"
        title={active ? detail.title(active) : ''}
        subtitle={active && detail.subtitle ? detail.subtitle(active) : undefined}
        eyebrow={active && detail.eyebrow ? detail.eyebrow(active) : undefined}
        footer={
        <>
              <Button variant="ghost" onClick={() => setActive(null)}>
                Close
              </Button>
              {active && detail.actions?.(active)}
            </>
        }>
        
          {active && detail.render(active)}
        </Drawer>
      }
    </div>);

}