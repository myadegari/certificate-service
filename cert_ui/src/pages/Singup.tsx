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
import { EyeOpenIcon, EyeClosedIcon } from '@radix-ui/react-icons';

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
import React, { useState } from "react";

const content = {
    usernameIsRequired: "نام کاربری الزامی است.",
    passwordIsRequired: "رمز عبور الزامی است.",
    confirmPasswordIsRequired: "تأیید رمز عبور الزامی است.",
    singupBtn: "ثبت نام",
    already: "قبلا ثبت نام کرده اید؟",
    login: "ورود",
    singupTitle: "ثبت نام در سامانه",
    singupDescription: "لطفا اطلاعات خود را برای ثبت نام وارد کنید."
}

const validationSchemaSignup = Yup.object().shape({
    username: Yup.string()
        .required(content.usernameIsRequired),
    password: Yup.string().required(content.passwordIsRequired),
    confirmPassword: Yup.string()
        .required('تأیید رمز عبور الزامی است.')
        .oneOf([Yup.ref('password'), ""], 'رمز عبور باید با تأیید رمز عبور مطابقت داشته باشد.')
});
type TSignupForm = Yup.InferType<typeof validationSchemaSignup>;
function Signup() {
    const navigate = useNavigate();
    const [showPassword, setShowPassword] = useState(false);

    const form = useForm<TSignupForm>({
        resolver: yupResolver(validationSchemaSignup)
    });

    const { control, handleSubmit, formState: { errors } } = form;

    const { mutate } = useMutation({
        mutationFn: (data: TSignupForm) => {
            return GeneralClient.post('/signup', data);
        },
        onSuccess: (response) => {
            console.log('Signup successful:', response);
            navigate(RoutesPaths.auth_verify, {
                replace: true,
                state: { user_id: response.data.user.id }

            })
            // Handle successful login, e.g., redirect or show a success message
        },
        onError: (error) => {
            console.error('Signup failed:', error);
            // Handle signup error, e.g., show an error message
        }
    });

    const onSubmit: SubmitHandler<TSignupForm> = data => {
        console.log('Form submitted:', data);
        mutate(data);
        // You can also handle form submission here if needed
    };

    const togglePasswordVisibility = () => {
        setShowPassword((prev) => !prev);
    };
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);
    const toggleConfirmPasswordVisibility = () => {
        setShowConfirmPassword((prev) => !prev);
    };

    return (
        <>
            <CardHeader>
                <CardTitle className="text-center">{content.singupTitle}</CardTitle>
                <CardDescription className="text-center">
                    {content.singupDescription}
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
                                        نام کاربری
                                    </FormLabel>
                                    <FormControl>
                                        <Input
                                            type="text"
                                            style={{ direction: 'ltr' }}
                                            // placeholder="نام کاربری"
                                            {...field}
                                        />
                                    </FormControl>
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
                        <FormField
                            control={control}
                            name="confirmPassword"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>
                                        تکرار رمز عبور
                                    </FormLabel>
                                    <div className="flex flex-row-reverse items-center justify-center gap-1">
                                        <FormControl>
                                            <Input
                                                type="password"
                                                style={{ direction: 'ltr' }}
                                                // placeholder="تکرار رمز عبور"
                                                {...field}
                                            />
                                        </FormControl>
                                        <span

                                            onClick={toggleConfirmPasswordVisibility}
                                            className="bg-slate-100 w-fit h-full flex items-center p-2 rounded-md cursor-pointer border-slate-300 border hover:bg-slate-300 transition-colors duration-200"
                                        >
                                            {showConfirmPassword ? <EyeOpenIcon /> : <EyeClosedIcon />}
                                        </span>
                                    </div>
                                    <FormMessage />
                                </FormItem>
                            )} />
                        <Button type="submit" className="w-full mt-4 cursor-pointer">
                            {content.singupBtn}
                        </Button>

                        <FormDescription className="text-center mt-2">{content.already}
                            <NavLink to={RoutesPaths.auth_login} className="text-blue-500 hover:underline">{content.login}</NavLink>
                        </FormDescription>
                    </form>
                </Form>
            </CardContent>
        </>
    )
} export default Signup;