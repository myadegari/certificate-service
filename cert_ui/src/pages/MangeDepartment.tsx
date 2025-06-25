import { Card, CardTitle, CardHeader, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { WandSparkles } from 'lucide-react'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import * as Yup from "yup";
import { yupResolver } from "@hookform/resolvers/yup";
import { useForm, type SubmitHandler } from "react-hook-form"
import { ScrollArea } from '@/components/ui/scroll-area'
function MangeDepartment() {
  const validationSchema = Yup.object().shape({
    department_name: Yup.string()
      .required(),
  });
  const content = {
    department_name: "نام واحد",

  }

  type TForm = Yup.InferType<typeof validationSchema>;
  const form = useForm<TForm>({
    resolver: yupResolver(validationSchema)
  });
  const { control, handleSubmit, formState: { errors } } = form;
  const onSubmit: SubmitHandler<TForm> = data => {
    console.log(data);
  };



  return (
    <div className='w-full p-5 sm:grid flex-col sm:grid-cols-12 gap-4 space-y-2'>
      <Card className='md:col-start-3 md:col-span-3 col-span-4'>
        <CardHeader>
          <CardTitle>
            لیست واحد ها
          </CardTitle>
          <Button className='mt-2 flex items-center justify-center gap-3' variant='outline' size='sm'>
            <WandSparkles />
            تعریف واحد جدید
          </Button>
        </CardHeader>
        <CardContent>

        </CardContent>
      </Card>
      <Card className='md:col-span-5 col-span-8 h-fit'>
        <CardHeader>
          <CardTitle>
            اطلاعات واحد
          </CardTitle>
        </CardHeader>
        <CardContent>
            <Form {...form}>
              <form onSubmit={handleSubmit(onSubmit)} className="space-y-2 px-1 place-content-center">
                <FormField
                  control={control}
                  name="department_name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel >
                        {content.department_name}
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
              <Button type='submit' className='w-full'>

              </Button>
              </form>
            </Form>
        </CardContent>
      </Card>
    </div>
  )
}
export default MangeDepartment