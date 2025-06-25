import { Card,CardTitle,CardHeader,CardDescription,CardContent } from '@/components/ui/card'
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import persian from "react-date-object/calendars/persian"
import persian_fa from "react-date-object/locales/persian_fa"
import DateObject from "react-date-object"
import {OctagonAlert,Heart,DoorOpen,LogOut,Settings,Layers2,UserCog, UserCog2,CircleUser } from "lucide-react"
import React from 'react'
import { Calendar } from "@/components/ui/calendar"

function UserPanel() {
  const content = {
    title:"پنل کاربری",
    greting:"به پنل کاربری خود خوش آمدید.",
    courses:{
      title:"گزارش وضعیت",
      description:"این گزارش فقط مربوط به سال جاری است.",
      courseCount:"تعداد دوره های شرکت کرده",
      courseDurations:"مدت زمان دوره های شرکت کرده",
      courseLeft:"مدت زمان کل",
    },
    today: new DateObject({
      calendar: persian,
      locale: persian_fa,
    })
  }
  return (
    <div className='w-full p-5'>
      <div className='sm:grid flex-col sm:grid-cols-12 grid-rows-5 gap-2'>
      <Card className='col-start-2 col-span-9 row-span-2'>
        <CardHeader>
          <CardTitle>اطلاعیه ها</CardTitle>
          {/* <CardDescription>اطلاعیه های مهم را در این بخش مشاهده کنید.</CardDescription> */}
        </CardHeader>
        <CardContent>
          <Alert variant="destructive" className='border-red-400'>
          <OctagonAlert/>
            <AlertTitle>توجه!</AlertTitle>
            <AlertDescription>این یک اطلاعیه تستی است.</AlertDescription>
          </Alert>
          
          
        </CardContent>
      </Card>
      {/* <Card className='sm:col-span-2 sm:row-span-1 row-span-full '> */}
      <Card className='col-start-2 col-span-3 row-start-3 grid place-content-center'>
       
        <CardContent className='flex items-center justify-center gap-2 text-sm'>
          <Heart size={15} className='text-red-600'/>
         {content.greting}
        </CardContent>
      </Card>
      <Card className='col-span-6 row-start-3 row-end-6 '>
        <CardHeader>
          <CardTitle>{content.courses.title}</CardTitle>
          <CardDescription>{content.courses.description}</CardDescription>
        </CardHeader>
        <CardContent className='flex  w-full justify-center gap-2 flex-wrap'>
              <div className='flex gap-2 border py-2 px-4 rounded-md'>

              <p>{content.courses.courseCount}:</p>
      
              <p>5</p>
              </div>
          
       
              <div className='flex gap-2 border py-2 px-4 rounded-md'>

              <p>{content.courses.courseDurations}:</p>

              <p className='flex gap-0.5'>5<span>ساعت</span></p>
              </div>
              {/* <div className='flex gap-2 border py-2 px-4 rounded-md'>

              <p>{content.courses.courseLeft}:</p>

              <p className='flex gap-0.5'>5<span>ساعت</span></p>
              </div> */}
        </CardContent>
      </Card>
      <Card className='col-start-2 row-start-4 col-span-3 row-end-6 flex items-center justify-center'>
        {/* <CardHeader>
          <CardTitle>{content.title}</CardTitle>
 
        </CardHeader> */}
        <CardContent>
          <div className='flex flex-col items-center justify-center gap-2'>
            <p className='text-xl'>{content.today.format("YYYY/MM/DD")}</p>
            <p className='text-lg'>{content.today.format("dddd")}</p>
          </div>
        </CardContent>
      </Card>
      
    
      </div>
    </div>
  )
}

export default UserPanel