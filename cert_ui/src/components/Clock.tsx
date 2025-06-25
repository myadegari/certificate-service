import React from "react";

import { cn } from "@/lib/utils";

function Clock({ className }: { className: string }) {
  const [dateState, setDateState] = React.useState(new Date());
  React.useEffect(() => {
    const interval = setInterval(() => {
      setDateState(new Date());
    }, 3000);
    return () => clearInterval(interval);
  }, []);
  return (
    <div className={cn("mt-3 cursor-default justify-self-center", className)}>
      {dateState.toLocaleString("fa-IR", {
        hour: "numeric",
        minute: "numeric",
        hour12: true,
      })}
    </div>
  );
}

export default Clock;