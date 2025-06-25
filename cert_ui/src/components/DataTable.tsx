import {
    type ColumnDef,
    flexRender,
    getCoreRowModel,
    useReactTable,
  } from "@tanstack/react-table";
  
  import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
  } from "@/components/ui/table";
  import { cn } from "@/lib/utils";
  
  import { Button } from "./ui/button";
  
  interface DataTableProps<TData, TValue> {
    columns: ColumnDef<TData, TValue>[];
    data: TData[];
    className?: string;
  }
  
  export function DataTable<TData, TValue>({
    columns,
    data,
    className,
  }: DataTableProps<TData, TValue>) {
    const table = useReactTable({
      data,
      columns,
      getCoreRowModel: getCoreRowModel(),

    });
  
    return (
      <>
        <div className={cn("rounded-xl border", className)}>
          <Table>
            <TableHeader>
              {table.getHeaderGroups().map((headerGroup) => (
                <TableRow
                  key={headerGroup.id}
                  className="border-light-border-primary hover:bg-light-background-accent dark:border-dark-border-primary dark:hover:bg-dark-background-accent"
                >
                  {headerGroup.headers.map((header) => {
                    return (
                      <TableHead key={header.id} className="sm:text-base">
                        {header.isPlaceholder
                          ? null
                          : flexRender(
                              header.column.columnDef.header,
                              header.getContext(),
                            )}
                      </TableHead>
                    );
                  })}
                </TableRow>
              ))}
            </TableHeader>
            <TableBody>
              {table.getRowModel().rows?.length ? (
                table.getRowModel().rows.map((row) => (
                  <TableRow
                    className="border-light-border-primary hover:bg-light-background-accent dark:border-dark-border-primary dark:hover:bg-dark-background-accent"
                    key={row.id}
                    data-state={row.getIsSelected() && "selected"}
                  >
                    {row.getVisibleCells().map((cell) => (
                      <TableCell key={cell.id}>
                        {flexRender(
                          cell.column.columnDef.cell,
                          cell.getContext(),
                        )}
                      </TableCell>
                    ))}
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell
                    colSpan={columns.length}
                    className="h-24 text-center"
                  >
                    اطلاعاتی وجود ندارد.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
        <div className="flex flex-col gap-2 py-5">
          <div className="pr-1">
            صفحه : {table.getState().pagination.pageIndex + 1} از{" "}
            {table.getPageCount()}
          </div>
          <div className="flex items-center gap-1">
            <Button
              variant="outline"
              className="border-light-border-primary dark:border-dark-border-primary"
              onClick={() => table.previousPage()}
              disabled={!table.getCanPreviousPage()}
            >
              قبل
            </Button>
            <Button
              variant="outline"
              className="border-light-border-primary dark:border-dark-border-primary"
              onClick={() => table.nextPage()}
              disabled={!table.getCanNextPage()}
            >
              بعد
            </Button>
          </div>
        </div>
      </>
    );

  }  
  export default DataTable;