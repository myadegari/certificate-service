
import {
    CardContent,
    CardFooter,
    CardHeader,
    CardTitle,
} from "@/components/ui/card"
import {
    InputOTP,
    InputOTPGroup,
    InputOTPSeparator,
    InputOTPSlot,
} from "@/components/ui/input-otp"
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
import { Button } from '@/components/ui/button';
import { useMutation } from "@tanstack/react-query";
import { GeneralClient } from "@/api/axios";
import RoutesPaths from "@/core/routes";
import { NavLink, useNavigate } from "react-router";
import { toast } from "react-toastify";
const content = {
    usernameIsRequired: "نام کاربری الزامی است.",
    passwordIsRequired: "رمز عبور الزامی است.",
    fas2IsRequired: "کد تایید الزامی است.",
    loginBtn: "این فرایند برای تایید حساب شما الزامی است.",
    loginTitle: "فراموشی رمز عبور",
    loginDescription: "کد شناسه دو عاملی را با استفاده از تلفن همراه خود اسکن  کرده و کد را در قسمت زیر وارد کنید.",
    dontHaveAccount: "حساب کاربری ندارید؟",
    submit: "تایید",
    back: "بازگشت به صفحه ورود",
    username: "نام کاربری",
    f2auth: "شناسه دو عاملی",
    forgotPassword: "فراموشی رمز عبور",
}

const validationSchemaLogin = Yup.object().shape({
    username: Yup.string()
        .required(content.usernameIsRequired),
    pin: Yup.string()
        .required(content.fas2IsRequired),
});

type TLoginForm = Yup.InferType<typeof validationSchemaLogin>;
function ForgetPassword() {

    const navigate = useNavigate();
    const form = useForm<TLoginForm>({
        resolver: yupResolver(validationSchemaLogin)
    });

    const { control } = form;
    const { mutate } = useMutation({
        mutationFn: (data: TLoginForm) => {
            return GeneralClient.post(`/otp/verify?username=${data.username}&otp=${data.pin}`);
        },
        onSuccess: (_response, variables) => {
            toast.success("حساب کاربری با موفقیت فعال شد")
            navigate(RoutesPaths.auth_changePassword, { replace: true, state: { username: variables.username } });

            // Handle successful login, e.g., redirect or show a success message
        },
        onError: (error) => {
            console.error('Login failed:', error);
            toast.error("خطا در ورود، لطفا دوباره تلاش کنید");
            // Handle login error, e.g., show an error message
        }
    });

    const onSubmit: SubmitHandler<TLoginForm> = data => {
        console.log('Form submitted:', data);
        // console.log('User ID:', location.state.user_id);
        mutate(data);
        // You can also handle form submission here if needed
    };

    return (
        <>
            <CardHeader>
                <CardTitle className="text-center">
                    {content.loginTitle}
                </CardTitle>

            </CardHeader>
            <CardContent className="space-y-4">
                <Form {...form}>

                    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                        <FormField
                            control={control}
                            name="username"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel >
                                        {content.username}
                                    </FormLabel>
                                    <FormControl>
                                        <Input
                                            type="text"
                                            style={{
                                                direction: "ltr"
                                            }}
                                            // placeholder="نام کاربری"
                                            {...field}
                                        />
                                    </FormControl>
                                    {/* <FormDescription>{errors.username && errors.username.message}</FormDescription> */}
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                        <FormField
                            control={form.control}
                            name="pin"
                            render={({ field }) => (
                                <FormItem className="flex flex-col lg:flex-row lg:gap-5 w-full">
                                    <FormLabel >
                                        {content.f2auth}
                                    </FormLabel>
                                    <FormControl>
                                        <div className=" grid lg:flex-1 place-content-center ">

                                            <InputOTP maxLength={6} {...field} >
                                                <InputOTPGroup>
                                                    <InputOTPSlot index={5} />
                                                    <InputOTPSlot index={4} />
                                                    <InputOTPSlot index={3} />
                                                </InputOTPGroup>
                                                <InputOTPSeparator />
                                                <InputOTPGroup>
                                                    <InputOTPSlot index={2} />
                                                    <InputOTPSlot index={1} />
                                                    <InputOTPSlot index={0} />
                                                </InputOTPGroup>
                                            </InputOTP>
                                        </div>
                                    </FormControl>
                                    {/* <FormDescription>{content.loginBtn}</FormDescription> */}
                                    <FormMessage />
                                </FormItem>
                            )}
                        />

                        <Button type="submit" className="w-full">{content.submit}</Button>
                    </form>
                </Form>
                <div className="w-full">

                    <Button variant={"outline"} className="w-full cursor-pointer">
                        <NavLink to={RoutesPaths.auth_login} className="w-full">
                            {content.back}
                        </NavLink>
                    </Button>
                </div>
            </CardContent>
            <CardFooter className="flex items-center flex-col justify-center">
                <img src="/2fas.webp" className="w-18 opacity-40 grayscale" />
            </CardFooter>
        </>
    )
} export default ForgetPassword