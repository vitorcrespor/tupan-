import {
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
} from '@tanstack/react-table';
import { atom, useAtom } from 'jotai';
import { ArrowDownIcon, ArrowUpIcon, ChevronsUpDownIcon } from 'lucide-react';
import React, { createContext, memo, useCallback, useContext } from 'react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  TableBody as TableBodyRaw,
  TableCell as TableCellRaw,
  TableHeader as TableHeaderRaw,
  TableHead as TableHeadRaw,
  Table as TableRaw,
  TableRow as TableRowRaw,
} from '@/components/ui/table';
import { cn } from '@/lib/utils';

const sortingAtom = atom(/** @type {import('@tanstack/react-table').SortingState} */ ([]));

/** @type {React.Context<{data: any[], columns: any[], table: import('@tanstack/react-table').Table<any> | null}>} */
export const TableContext = createContext({
  data: [],
  columns: [],
  table: null,
});

/** @param {{columns: any[], data: any[], children: React.ReactNode, className?: string}} props */
export function TableProvider({ columns, data, children, className = '' }) {
  const [sorting, setSorting] = useAtom(sortingAtom);
  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    onSortingChange: (updater) => {
      setSorting((current) => typeof updater === 'function' ? updater(current) : updater);
    },
    state: { sorting },
  });

  return (
    <TableContext.Provider value={{ data, columns, table }}>
      <TableRaw className={className}>{children}</TableRaw>
    </TableContext.Provider>
  );
}

/** @param {{header: any, className?: string}} props */
const TableHeadView = ({ header, className = '' }) => (
  <TableHeadRaw className={className} key={header.id}>
    {header.isPlaceholder
      ? null
      : flexRender(header.column.columnDef.header, header.getContext())}
  </TableHeadRaw>
);
export const TableHead = memo(TableHeadView);
TableHead.displayName = 'TableHead';

/** @param {{headerGroup: any, children: (value: {header: any}) => React.ReactNode}} props */
export function TableHeaderGroup({ headerGroup, children }) {
  return (
    <TableRowRaw key={headerGroup.id}>
      {headerGroup.headers.map((header) => children({ header }))}
    </TableRowRaw>
  );
}

/** @param {{className?: string, children: (value: {headerGroup: any}) => React.ReactNode}} props */
export function TableHeader({ className = '', children }) {
  const { table } = useContext(TableContext);
  return (
    <TableHeaderRaw className={className}>
      {table?.getHeaderGroups().map((headerGroup) => children({ headerGroup }))}
    </TableHeaderRaw>
  );
}

/** @param {{column: any, title: React.ReactNode, className?: string}} props */
export function TableColumnHeader({ column, title, className = '' }) {
  const handleSortAsc = useCallback(() => column.toggleSorting(false), [column]);
  const handleSortDesc = useCallback(() => column.toggleSorting(true), [column]);

  if (!column.getCanSort()) {
    return <div className={cn(className)}>{title}</div>;
  }

  return (
    <div className={cn('flex items-center space-x-2', className)}>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button className="-ml-3 h-8 data-[state=open]:bg-accent" size="sm" variant="ghost">
            <span>{title}</span>
            {column.getIsSorted() === 'desc' ? (
              <ArrowDownIcon className="ml-2 h-4 w-4" />
            ) : column.getIsSorted() === 'asc' ? (
              <ArrowUpIcon className="ml-2 h-4 w-4" />
            ) : (
              <ChevronsUpDownIcon className="ml-2 h-4 w-4" />
            )}
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start">
          <DropdownMenuItem onClick={handleSortAsc}>
            <ArrowUpIcon className="mr-2 h-3.5 w-3.5 text-muted-foreground/70" />
            Asc
          </DropdownMenuItem>
          <DropdownMenuItem onClick={handleSortDesc}>
            <ArrowDownIcon className="mr-2 h-3.5 w-3.5 text-muted-foreground/70" />
            Desc
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}

/** @param {{cell: any, className?: string}} props */
export function TableCell({ cell, className = '' }) {
  return (
    <TableCellRaw className={className}>
      {flexRender(cell.column.columnDef.cell, cell.getContext())}
    </TableCellRaw>
  );
}

/** @param {{row: any, children: (value: {cell: any}) => React.ReactNode, className?: string, [key: string]: any}} props */
export function TableRow({ row, children, className = '', ...props }) {
  return (
    <TableRowRaw className={className} data-state={row.getIsSelected() && 'selected'} key={row.id} {...props}>
      {row.getVisibleCells().map((cell) => children({ cell }))}
    </TableRowRaw>
  );
}

/** @param {{children: (value: {row: any}) => React.ReactNode, className?: string}} props */
export function TableBody({ children, className = '' }) {
  const { columns, table } = useContext(TableContext);
  const rows = table?.getRowModel().rows;
  return (
    <TableBodyRaw className={className}>
      {rows?.length ? (
        rows.map((row) => children({ row }))
      ) : (
        <TableRowRaw>
          <TableCellRaw className="h-24 text-center" colSpan={columns.length}>
            No results.
          </TableCellRaw>
        </TableRowRaw>
      )}
    </TableBodyRaw>
  );
}
