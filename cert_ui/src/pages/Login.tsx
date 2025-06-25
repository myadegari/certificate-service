
import {
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card"
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
import { NavLink, useLocation, useNavigate } from "react-router";
import { useState } from "react";
import { EyeClosedIcon, EyeOpenIcon } from "@radix-ui/react-icons";
const content = {
    usernameIsRequired: "نام کاربری الزامی است.",
    passwordIsRequired: "رمز عبور الزامی است.",
    loginBtn: "ورود",
    loginTitle: "ورود به سامانه",
    loginDescription: "لطفا اطلاعات خود را برای ورود وارد کنید.",
    dontHaveAccount: "حساب کاربری ندارید؟",
    register: "ثبت نام",
    username: "نام کاربری",
    password: "رمز عبور",
    forgotPassword: "فراموشی رمز عبور",
}

const validationSchemaLogin = Yup.object().shape({
    username: Yup.string()
        .required(content.usernameIsRequired),
    password: Yup.string().required(content.passwordIsRequired),
});

type TLoginForm = Yup.InferType<typeof validationSchemaLogin>;
function Login() {
    const { userLogin, Auth } = useAuthentication();
    const navigate = useNavigate();
    const location = useLocation();
    const from = location.state?.from?.pathname ?? RoutesPaths.user_panel;
    const form = useForm<TLoginForm>({
        resolver: yupResolver(validationSchemaLogin)
    });

    const { control, handleSubmit, formState: { errors } } = form;

    const { mutate } = useMutation({
        mutationFn: (data: TLoginForm) => {
            return GeneralClient.post('/login', data);
        },
        onSuccess: (response) => {
            console.log('Login successful:', response);
            userLogin(response, from);
            // Handle successful login, e.g., redirect or show a success message
        },
        onError: (error) => {
            console.error('Login failed:', error);
            // Handle login error, e.g., show an error message
        }
    });

    const onSubmit: SubmitHandler<TLoginForm> = data => {
        console.log('Form submitted:', data);
        mutate(data);
        // You can also handle form submission here if needed
    };
    const [showPassword, setShowPassword] = useState(false);
    const togglePasswordVisibility = () => {
        setShowPassword(!showPassword);
    };

    return (
        <>
            <CardHeader>
                <CardTitle className="text-center">
                    {content.loginTitle}
                </CardTitle>
                <CardDescription className="text-center">
                    {content.loginDescription}
                </CardDescription>
            </CardHeader>
            <CardContent>
                <Form {...form}>
                    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
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
                            control={control}
                            name="password"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>
                                        رمز عبور
                                    </FormLabel>
                                    <div className="flex flex-row-reverse items-center justify-center gap-1">

                                        <FormControl>
                                            <Input
                                                type={showPassword ? "text" : "password"}
                                                style={{ direction: 'ltr' }}
                                                // placeholder="رمز عبور"
                                                {...field}
                                            />
                                        </FormControl>
                                        <span

                                            onClick={togglePasswordVisibility}
                                            className="bg-slate-100 w-fit h-full flex items-center p-2 rounded-md cursor-pointer border-slate-300 border hover:bg-slate-300 transition-colors duration-200"
                                        >
                                            {showPassword ? <EyeOpenIcon /> : <EyeClosedIcon />}
                                        </span>
                                    </div>
                                    <FormMessage />
                                </FormItem>
                            )} />
                        <Button type="submit" className="w-full mt-4 cursor-pointer">
                            {content.loginBtn}
                        </Button>
                        <Button variant={"outline"} className="w-full cursor-pointer" onClick={() => navigate(RoutesPaths.auth_forgetPassword)}>
                            {content.forgotPassword}
                        </Button>
                        <FormDescription className="text-center mt-2">
                            {content.dontHaveAccount} <NavLink to={RoutesPaths.auth_register} className="text-blue-500 hover:underline">{content.register}</NavLink>
                        </FormDescription>
                    </form>
                </Form>
            </CardContent>
        </>
    )
} export default Login