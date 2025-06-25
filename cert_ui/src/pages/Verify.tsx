
import {
    CardContent,
    CardDescription,
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
import { Button } from '@/components/ui/button';
import { useMutation, useQuery } from "@tanstack/react-query";
import { GeneralClient } from "@/api/axios";
import { useAuthentication } from "@/context/authenticationContext";
import RoutesPaths from "@/core/routes";
import { NavLink, useLocation, useNavigate, useParams } from "react-router";
import { toast } from "react-toastify";
const content = {
    usernameIsRequired: "نام کاربری الزامی است.",
    passwordIsRequired: "رمز عبور الزامی است.",
    loginBtn: "این فرایند برای تایید حساب شما الزامی است.",
    loginTitle: "کد تایید شناسه دو عاملی",
    loginDescription: "تصویر زیر را با برنامه 2FAS اسکن نمایید.",
    dontHaveAccount: "حساب کاربری ندارید؟",
    register: "ارسال کد",
    username: "نام کاربری",
    password: "رمز عبور",
    forgotPassword: "فراموشی رمز عبور",
    recomended: "برنامه توصیه شده برای این کار 2FAS می باشد که می توانید از طریق لینک زیر آن را دانلود کنید.",
}

const validationSchemaLogin = Yup.object().shape({
    pin: Yup.string()
        .required(content.usernameIsRequired),
});

type TLoginForm = Yup.InferType<typeof validationSchemaLogin>;
function Verify() {

    const navigate = useNavigate();
    const location = useLocation();
    const from = location.state?.from?.pathname ?? RoutesPaths.user_panel;
    const form = useForm<TLoginForm>({
        resolver: yupResolver(validationSchemaLogin)
    });

    const { control, handleSubmit, formState: { errors } } = form;
    const { isLoading, isError, data: queryData } = useQuery({
        queryKey: ['otpData'],
        queryFn: () => GeneralClient.get('/otp/generate', {
            params: {
                user_id: 4 //location.state.user_id,
            }
        }),
        // enabled: !!Auth.accessToken, // Only fetch if accessToken is available
    });
    const { mutate } = useMutation({
        mutationFn: (data: TLoginForm) => {
            return GeneralClient.post(`/otp/verify?user_id=${location.state.user_id}&otp=${data.pin}`);
        },
        onSuccess: (response) => {
            // console.log('Login successful:', response);
            toast.success("حساب کاربری با موفقیت فعال شد")
            navigate(RoutesPaths.auth_login, { replace: true });

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
        console.log('User ID:', location.state.user_id);
        mutate(data);
        // You can also handle form submission here if needed
    };
    if (isLoading) {
        return <div>Loading...</div>;
    }
    if (isError) {
        return <div>Error loading data</div>;
    }
    console.log('Data loaded:', queryData);
    return (
        <>
            <CardHeader>
                <CardTitle className="text-center">
                    {content.loginTitle}
                </CardTitle>
                <CardDescription className="text-center font-estedad">
                    {content.loginDescription}
                </CardDescription>
            </CardHeader>
            <CardContent className="grid place-items-center ">
                {/* how can i show this image? */}
                <img src={`/${queryData?.data.qrcode}`} style={{ width: '35%', height: 'auto' }} alt="" className="mb-5" />
                <Form {...form}>

                    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                        <FormField
                            control={form.control}
                            name="pin"
                            render={({ field }) => (
                                <FormItem>
                                    <FormControl>
                                        <InputOTP maxLength={6} {...field}>
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
                                    </FormControl>
                                    <FormDescription>{content.loginBtn}</FormDescription>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />

                        <Button type="submit" className="w-full">{content.register}</Button>
                    </form>
                </Form>
            </CardContent>
            <CardFooter className="flex items-center flex-col justify-center">
                <img src="/2fas.webp" className="w-18 opacity-40 grayscale" />
            </CardFooter>
        </>
    )
} export default Verify