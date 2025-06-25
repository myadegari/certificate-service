import { SidebarProvider, SidebarTrigger } from '@/components/ui/sidebar'
import { Outlet } from 'react-router'
import { AppSidebar } from './AppSidebar'
// import React from 'react'
// 
function UserPanelLayout() {
  return (
    <SidebarProvider>
    <AppSidebar />
    <main className='bg-slate-100 w-full  flex p-2 '>
      <SidebarTrigger />
   <Outlet/>
    </main>
  </SidebarProvider>
  )
}

export default UserPanelLayout