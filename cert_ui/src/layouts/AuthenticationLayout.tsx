import React from 'react'
import {
    Card,
    CardContent,
    CardDescription,
    CardFooter,
    CardHeader,
    CardTitle,
  } from "@/components/ui/card"
import { Outlet } from 'react-router'
  

function AuthenticationLayout() {
  return (
    <div className='bg-slate-400 h-screen flex items-center justify-center'>
       <Card className='lg:w-[400px] lg:text-3xl lg:min-h-[500px] lg:pt-15'>
<Outlet />
</Card>

        </div>
  )
}

export default AuthenticationLayout