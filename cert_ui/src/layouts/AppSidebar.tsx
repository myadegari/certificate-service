import { Command, Home, Inbox, SlidersHorizontal, Settings,Layers2, Armchair, Users } from "lucide-react"

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"
import Clock from "@/components/Clock"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Link, useLocation } from "react-router"
import RoutesPaths from "@/core/routes"
import { cn } from "@/lib/utils"

// Menu items.
const items = [
  {
    title:"پنل کاربری",
    url:"/user-panel",
    icon:Home
  },
  {
    title: "گواهی دوره ها",
    url: "/certs",
    icon: Layers2,
  },
 
  {
    title: "ویرایش پروفایل",
    url: "/profile",
    icon: Settings,
  }
]

const adminItems=[
  {
    title:"مدیریت کاربران",
    url:"/user-management",
    icon:Users,
  },
  {
    title:"تعریف واحد",
    url:"/department",
    icon:Armchair
  },
  {
    title:"تعریف دوره",
    url:"/create-course",
    icon:Command,
  }
]
export function AppSidebar() {
  const location = useLocation();
  return (
    <Sidebar side="right" >
      <SidebarContent className="bg-slate-200">
        <SidebarGroup className="mt-5" >
          <SidebarGroupContent>
            <SidebarMenu>
              {items.map((item) =>{
                const isActive = location.pathname === item.url;
                return(
                <SidebarMenuItem key={item.title}>
                  <Link to={item.url}>
                        <SidebarMenuButton className={cn("flex items-center gap-4 px-4 h-10 ",isActive?"bg-slate-100":"cursor-pointer ")} >
                        <item.icon />
                        <span>{item.title}</span>
                    </SidebarMenuButton>
                    </Link>
                </SidebarMenuItem>
              )})}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
        {/* Admin items, only visible to admin users */}
        <SidebarGroup className="border-t border-slate-300 my-4" >
          <SidebarGroupLabel>پنل مدیریت</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {adminItems.map((item) =>{
                const isActive = location.pathname === item.url;
                return(
                <SidebarMenuItem key={item.title}>
                  <Link to={item.url}>
                        <SidebarMenuButton className={cn("flex items-center gap-4 px-4 h-10 ",isActive?"bg-slate-100":"cursor-pointer ")} >
                        <item.icon />
                        <span>{item.title}</span>
                    </SidebarMenuButton>
                    </Link>
                </SidebarMenuItem>
              )})}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter className="flex items-center justify-between bg-slate-200 p-4">
      <Avatar>
  <AvatarImage src="https://github.com/shadcn.png" />
  <AvatarFallback>CN</AvatarFallback>
</Avatar>
    <Clock className="text-gray-500"/>
    </SidebarFooter> 
    </Sidebar>
  )
}