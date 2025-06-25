import React from "react";
import { FaFilter } from "react-icons/fa6";
import { CaretSortIcon } from "@radix-ui/react-icons";
import { type RankingInfo, rankItem } from "@tanstack/match-sorter-utils";
import {
  type ColumnDef,
  type ColumnFiltersState,
  type FilterFn,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  type SortingState,
  useReactTable,
  type VisibilityState,
} from "@tanstack/react-table";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import useMediaQuery from "@/hooks/useMediaQuery";
import { cn } from "@/lib/utils";

// import CreateUser from "./CreateUser";

interface DataTableProps<TData, TValue> {
  columns: ColumnDef<TData, TValue>[];
  data: TData[];
  className?: string;
}
declare module "@tanstack/react-table" {
  //add fuzzy filter to the filterFns
  interface FilterFns {
    fuzzy: FilterFn<unknown>;
  }
  interface FilterMeta {
    itemRank: RankingInfo;
  }
}

export default function UserTable<TData, TValue>({
  columns,
  data,
  className,
}: DataTableProps<TData, TValue>) {
  const [sorting, setSorting] = React.useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = React.useState<ColumnFiltersState>(
    [],
  );
  const fuzzyFilter: FilterFn<TData> = (row, columnId, value, addMeta) => {
    // Rank the item
    const itemRank = rankItem(row.getValue(columnId), value);

    // Store the itemRank info
    addMeta({
      itemRank,
    });

    // Return if the item should be filtered in/out
    return itemRank.passed;
  };
  interface IVisibleColumns {
    id?: string;
    accessorKey?: string;
    header: string;
    cell: () => HTMLDivElement;
    enableHiding?: boolean;
  }
  const isMobile = useMediaQuery("(max-width: 768px)");
  const visibleColumns = isMobile
    ? columns.filter(
        (col) =>
          col?.id === "email" ||
          col?.id === "is_active" ||
          col?.id === "actions",
      )
    : columns;

  const [columnVisibility, setColumnVisibility] =
    React.useState<VisibilityState>({});
  const [rowSelection, setRowSelection] = React.useState({});
  const [globalFilter, setGlobalFilter] = React.useState("");
  const table = useReactTable({
    data,
    columns: visibleColumns as typeof columns,
    // onGlobalFilterChange:setGlobalFilter
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    onColumnVisibilityChange: setColumnVisibility,
    onRowSelectionChange: setRowSelection,
    filterFns: {
      fuzzy: fuzzyFilter,
    },
    state: {
      sorting,
      columnFilters,
      columnVisibility,
      rowSelection,
      globalFilter,
    },
  });

  return (
    <>
      <div className="flex gap-2 py-4">
        <Input
          placeholder="فیلتر بر اساس رایانامه ..."
          value={(table.getColumn("email")?.getFilterValue() as string) ?? ""}
          onChange={(event) =>
            table.getColumn("email")?.setFilterValue(event.target.value)
          }
          className="max-w-sm border-light-border-primary transition-colors duration-300 placeholder:text-light-text-placeholder focus:border-light-border-focus active:border-light-border-focus dark:border-dark-border-primary dark:placeholder:text-dark-text-placeholder dark:focus:border-dark-border-focus dark:active:border-dark-border-focus"
        />
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="outline"
              className="ml-auto border-light-border-primary bg-transparent hover:bg-light-background-accent dark:border-dark-border-primary dark:hover:bg-dark-background-accent"
            >
              <FaFilter />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent
            className="bg-light-background-accent dark:bg-dark-background-accent"
            align="end"
          >
            {table
              .getAllColumns()
              .filter((column) => column.getCanHide())
              .map((column) => {
                return (
                  <DropdownMenuCheckboxItem
                    key={column.id}
                    className="cursor-pointer capitalize hover:bg-light-background-secondary dark:hover:bg-dark-background-secondary"
                    style={{ direction: "rtl" }}
                    checked={column.getIsVisible()}
                    onCheckedChange={(value) =>
                      column.toggleVisibility(!!value)
                    }
                  >
                    {column.columnDef.header?.toString() ?? ""}
                  </DropdownMenuCheckboxItem>
                );
              })}
          </DropdownMenuContent>
        </DropdownMenu>
        {/* <CreateUser /> */}
      </div>
      <div className={cn("rounded-md border", className)}>
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow
                key={headerGroup.id}
                className="hover:bg-light-background-accent dark:hover:bg-dark-background-accent"
              >
                {headerGroup.headers.map((header) => {
                  return (
                    <TableHead key={header.id} className="text-base font-bold">
                      <div className="flex items-center gap-1">
                        {header.isPlaceholder
                          ? null
                          : flexRender(
                              header.column.columnDef.header,
                              header.getContext(),
                            )}
                        {header.column.getCanSort() ? (
                          <CaretSortIcon
                            onClick={header.column.getToggleSortingHandler()}
                          />
                        ) : (
                          ""
                        )}
                        {
                          { asc: "🔼", desc: "🔽" }[
                            header.column.getIsSorted() as "asc" | "desc"
                          ]
                        }
                      </div>
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
                  className="hover:bg-light-background-accent dark:hover:bg-dark-background-accent"
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
              <TableRow className="hover:bg-light-background-accent dark:hover:bg-dark-background-accent">
                <TableCell
                  colSpan={columns.length}
                  className="h-24 text-center"
                >
                  کاربری وجود ندارد.
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
            // size="sm"
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