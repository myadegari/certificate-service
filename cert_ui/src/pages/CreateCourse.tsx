import React from 'react'
import { Card,CardTitle,CardHeader,CardDescription,CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Check, ChevronsUpDown, WandSparkles } from 'lucide-react'
import DatePicker from "react-multi-date-picker"
import persian from "react-date-object/calendars/persian"
import persian_fa from "react-date-object/locales/persian_fa"

import {
    Form,
    FormControl,
    FormDescription,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import * as Yup from "yup";
import { yupResolver } from "@hookform/resolvers/yup";
import { useForm, type SubmitHandler } from "react-hook-form"
import {
    Command,
    CommandEmpty,
    CommandGroup,
    CommandInput,
    CommandItem,
    CommandList,
  } from "@/components/ui/command"
  import {
    Popover,
    PopoverContent,
    PopoverTrigger,
  } from "@/components/ui/popover"
import { cn } from '@/lib/utils'
import { ScrollArea } from '@/components/ui/scroll-area'
function CreateCourse() {
    const validationSchema = Yup.object().shape({
        course_name: Yup.string()
            .required(),
        course_date: Yup.string().required(),
        course_duration: Yup.string().required(),
        course_department: Yup.string().required(),
        course_indicator: Yup.object().shape({
            part1: Yup.string().required("Part 1 is required"),
            part2: Yup.string().required("Part 2 is required"),
            part3: Yup.string().required("Part 3 is required"),
        }).required(),
        course_signatory: Yup.array().of(Yup.string()).required(),
        course_participants: Yup.array().of(Yup.string()).required(),
    });
    const content={
        course_name: "نام دوره",
        course_date: "تاریخ برگزاری دوره",
        course_duration: "مدت زمان دوره",
        course_department: "واحد متولی دوره",
        course_indicator: "اندیکاتور دوره",
        course_signatory: "امضاکنندگان دوره",
        course_participants: "شرکت کنندگان دوره"
    }
    
    type TForm = Yup.InferType<typeof validationSchema>;
    const form = useForm<TForm>({
        resolver: yupResolver(validationSchema)
    });
    const { control, handleSubmit, formState: { errors } } = form;
    const onSubmit: SubmitHandler<TForm> = data => {
        console.log(data);
    };
    
const languages = [
    { label: "English", value: "en" },
    { label: "French", value: "fr" },
    { label: "German", value: "de" },
    { label: "Spanish", value: "es" },
    { label: "Portuguese", value: "pt" },
    { label: "Russian", value: "ru" },
    { label: "Japanese", value: "ja" },
    { label: "Korean", value: "ko" },
    { label: "Chinese", value: "zh" },
  ] as const
    
    return (
      <div className='w-full p-5 sm:grid flex-col sm:grid-cols-12 gap-4 space-y-2'>
          <Card className='md:col-start-3 md:col-span-3 col-span-4'>
            <CardHeader>
                <CardTitle>
                    لیست دوره ها
                </CardTitle>
                <Button className='mt-2 flex items-center justify-center gap-3' variant='outline' size='sm'>
                    <WandSparkles/>
                    تعریف دوره جدید  
                </Button>
            </CardHeader>
            <CardContent>

            </CardContent>
          </Card>
          <Card className='md:col-span-5 col-span-8'>
            <CardHeader>
                <CardTitle>
                    اطلاعات دوره
                </CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea dir='rtl' className=' h-[450px] grid place-content-center'>
            <Form {...form}>
                    <form onSubmit={handleSubmit(onSubmit)} className="space-y-2 mr-5 w-[90%] place-content-center">
                        <FormField
                            control={control}
                            name="course_name"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel >
                                        {content.course_name}
                                    </FormLabel>
                                    <FormControl>
                                        <Input
                                            type="text"
                                            style={{
                                                direction: "ltr"
                                            }}
                                            {...field}
                                        />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                       
                       {/*use react-multi-date-picker for date selection */}
                       <FormField
                control={control}
                name="course_date"
                render={({ field }) => (
                    <FormItem>
                        <FormLabel>
                            {content.course_date}
                        </FormLabel>
                        <FormControl>
                            <DatePicker
                                value={field.value}
                                onChange={(date) => {
                                    field.onChange(date?.isValid ? date.format() : '')
                                }}
                                maxDate={new Date()}
                                calendar={persian}
                                locale={persian_fa}
                                calendarPosition="bottom-right"
                                containerClassName="w-full"
                                inputClass="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                                style={{direction:"ltr"}}
                            />
                        </FormControl>
                        <FormMessage />
                    </FormItem>
                )}
            />
                        <FormField
                            control={control}
                            name="course_duration"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel >
                                        {content.course_duration}
                                    </FormLabel>
                                    <FormControl>
                                        <Input
                                            type="text"
                                            style={{
                                                direction: "ltr"
                                            }}
                                            {...field}
                                        />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                        <FormField
                            control={control}
                            name="course_department"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel >
                                        {content.course_department}
                                    </FormLabel>
                                    <FormControl>
                                        <Input
                                            type="text"
                                            style={{
                                                direction: "ltr"
                                            }}
                                            {...field}
                                        />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                        <div className="flex gap-5  flex-row-reverse">
  <FormField
    control={control}
    name="course_indicator.part1"
    render={({ field }) => (
      <FormItem className="w-1/3">
        <FormLabel className="opacity-0">Hidden</FormLabel>
        <FormControl>
          <Input type="text" style={{ direction: "ltr" }} {...field}  />
        </FormControl>
        <FormMessage />
      </FormItem>
    )}
  />

  <FormField
    control={control}
    name="course_indicator.part2"
    render={({ field }) => (
      <FormItem className="w-1/3">
        <FormLabel className="opacity-0">Hidden</FormLabel> {/* Keeps layout aligned */}
        <FormControl>
          <Input type="text" style={{ direction: "ltr" }} {...field} />
        </FormControl>
        <FormMessage />
      </FormItem>
    )}
  />

  <FormField
    control={control}
    name="course_indicator.part3"
    render={({ field }) => (
      <FormItem className="w-1/3">
        <FormLabel>{content.course_indicator}</FormLabel>
        <FormControl>
          <Input type="text" style={{ direction: "ltr" }} {...field} />
        </FormControl>
        <FormMessage />
      </FormItem>
    )}
  />
</div>
<FormField
  control={control}
  name="course_signatory"
  render={({ field }) => (
    <FormItem className="flex flex-col">
      <FormLabel>Signatories</FormLabel>
      <Popover>
        <PopoverTrigger asChild>
          <FormControl>
            <Button
              variant="outline"
              role="combobox"
              className={cn(
                "w-[300px] justify-between",
                (!field.value || field.value.length === 0) && "text-muted-foreground"
              )}
            >
              {field.value && field.value.length > 0
                ? languages
                    .filter((l) => field.value.includes(l.value))
                    .map((l) => l.label)
                    .join(", ")
                : "Select signatories"}
              <ChevronsUpDown className="opacity-50 ml-2" />
            </Button>
          </FormControl>
        </PopoverTrigger>

        <PopoverContent className="w-[300px] p-0">
          <Command>
            <CommandInput placeholder="Search signatories..." className="h-9" />
            <CommandList>
              <CommandEmpty>No signatory found.</CommandEmpty>
              <CommandGroup>
                {languages.map((language) => {
                  const isSelected = field.value?.includes(language.value);
                  return (
                    <CommandItem
                      key={language.value}
                      value={language.label}
                      onSelect={() => {
                        const current = field.value || [];
                        const updated = isSelected
                          ? current.filter((val) => val !== language.value)
                          : [...current, language.value];
                        field.onChange(updated);
                      }}
                    >
                      {language.label}
                      <Check
                        className={cn(
                          "ml-auto",
                          isSelected ? "opacity-100" : "opacity-0"
                        )}
                      />
                    </CommandItem>
                  );
                })}
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>

      <FormDescription>
        You can choose multiple signatories for the certificate.
      </FormDescription>
      <FormMessage />
    </FormItem>
  )}
/>
<FormField
  control={control}
  name="course_signatory"
  render={({ field }) => (
    <FormItem className="flex flex-col">
      <FormLabel>Signatories</FormLabel>
      <Popover>
        <PopoverTrigger asChild>
          <FormControl>
            <Button
              variant="outline"
              role="combobox"
              className={cn(
                "w-[300px] justify-between",
                (!field.value || field.value.length === 0) && "text-muted-foreground"
              )}
            >
              {field.value && field.value.length > 0
                ? languages
                    .filter((l) => field.value.includes(l.value))
                    .map((l) => l.label)
                    .join(", ")
                : "Select signatories"}
              <ChevronsUpDown className="opacity-50 ml-2" />
            </Button>
          </FormControl>
        </PopoverTrigger>

        <PopoverContent className="w-[300px] p-0">
          <Command>
            <CommandInput placeholder="Search signatories..." className="h-9" />
            <CommandList>
              <CommandEmpty>No signatory found.</CommandEmpty>
              <CommandGroup>
                {languages.map((language) => {
                  const isSelected = field.value?.includes(language.value);
                  return (
                    <CommandItem
                      key={language.value}
                      value={language.label}
                      onSelect={() => {
                        const current = field.value || [];
                        const updated = isSelected
                          ? current.filter((val) => val !== language.value)
                          : [...current, language.value];
                        field.onChange(updated);
                      }}
                    >
                      {language.label}
                      <Check
                        className={cn(
                          "ml-auto",
                          isSelected ? "opacity-100" : "opacity-0"
                        )}
                      />
                    </CommandItem>
                  );
                })}
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>

      <FormDescription>
        You can choose multiple signatories for the certificate.
      </FormDescription>
      <FormMessage />
    </FormItem>
  )}
/>
                    </form>
                </Form>
                </ScrollArea>
            </CardContent>
          </Card>
      </div>
  )
}
export default CreateCourse