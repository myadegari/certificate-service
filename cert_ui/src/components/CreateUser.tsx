import { type SubmitHandler, useForm } from "react-hook-form";
import { toast } from "react-toastify";
import { yupResolver } from "@hookform/resolvers/yup";
import { PlusCircledIcon } from "@radix-ui/react-icons";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import * as Yup from "yup";

import { ADNIM_USER_MANAGEMENT } from "@/api/server";
import PasswordInput from "@/components/PasswordInput";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
// import faContent, { passwordStates } from "@/constant/faFixContents";
import useAxiosPrivate from "@/hooks/useAxiosPrivate";

export default function CreateUser() {
  const validationSchemaPhone = Yup.object().shape({
    mobile_number: Yup.string()
      .length(11, "شماره تلفن باید یازده رقم باشد.")
      .required(passwordStates.phoneNumberIsRequired),
    password: Yup.string()
      .required(passwordStates.passwordIsRequired)
      .min(8, passwordStates.passwordMinLength),

    confirm_password: Yup.string()
      .required(passwordStates.repeatPasswordRequired)
      .oneOf([Yup.ref("password")], passwordStates.passwordsNotMatch),
  });
  const validationSchemaEmail = Yup.object().shape({
    email: Yup.string().email().required(passwordStates.emailIsRequired),
    password: Yup.string()
      .required(passwordStates.passwordIsRequired)
      .min(8, passwordStates.passwordMinLength),

    confirm_password: Yup.string()
      .required(passwordStates.repeatPasswordRequired)
      .oneOf([Yup.ref("password")], passwordStates.passwordsNotMatch),
  });

  type TEmailForm = Yup.InferType<typeof validationSchemaEmail>;
  type TPhoneForm = Yup.InferType<typeof validationSchemaPhone>;
  type TAxiosError = {
    response: {
      data: {
        message: string;
      };
    };
  };
  const queryClient = useQueryClient();
  const axiosPrivate = useAxiosPrivate();

  const userCreation = useMutation({
    mutationFn: async (userData: TPhoneForm | TEmailForm) => {
      await axiosPrivate({
        method: "post",
        url: ADNIM_USER_MANAGEMENT,
        data: userData,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      toast.success("کاربر با موفقیت ایجاد شد");
    },
    onError: (error: TAxiosError) => {
      toast.error(
        error.response?.data.message || "خطایی در ایجاد کاربر رخ داد",
      );
    },
  });

  const {
    register: emailRegister,
    handleSubmit: emailSubmit,
    formState: { errors: emailErrors },
  } = useForm<TEmailForm>({
    resolver: yupResolver(validationSchemaEmail),
    criteriaMode: "all",
  });
  const handleSubmitEmail: SubmitHandler<TEmailForm> = (data) => {
    userCreation.mutate(data);
  };
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button
          variant="outline"
          className="flex gap-2 border-light-border-primary bg-transparent hover:bg-light-background-accent dark:border-dark-border-primary dark:hover:bg-dark-background-accent"
        >
          افزودن کاربر
          <PlusCircledIcon />
        </Button>
      </DialogTrigger>
      <DialogContent className="border-light-border-primary bg-light-background-secondary text-light-text-primary dark:border-dark-border-primary dark:bg-dark-background-accent dark:text-dark-text-primary sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>افزودن کاربر</DialogTitle>
        </DialogHeader>
        <form
          className="grid gap-2 py-1"
          onSubmit={emailSubmit(handleSubmitEmail)}
        >
          <label className="flex flex-col gap-2">
            {faContent.email}
            <Input
              {...emailRegister("email")}
              className="w-full gap-2 rounded-xl border-2 border-light-border-primary outline-none transition-colors duration-300 focus:border-light-border-focus dark:border-dark-border-primary dark:focus:border-dark-border-focus"
              style={{ direction: "ltr" }}
              type="email"
              name="email"
            />
          </label>
          {emailErrors.email ? (
            <p className="text-sm font-semibold text-red-500">
              {emailErrors.email.message}
            </p>
          ) : (
            ""
          )}
          <label className="flex flex-col gap-2">
            {faContent.password}
            <PasswordInput
              {...emailRegister("password")}
              className="flex flex-col gap-3"
              containerStyle="shadow-none py-1 pr-2 rounded-xl bg-transparent"
              name="password"
            />
          </label>
          {emailErrors.password && emailErrors.password.types && (
            <ul>
              {Object.values(emailErrors.password.types).map(
                (message, index) => (
                  <li
                    className="text-sm font-semibold text-red-500"
                    key={index}
                  >
                    - {message}
                  </li>
                ),
              )}
            </ul>
          )}
          <label className="flex flex-col gap-2">
            {faContent.repeatPassword}
            <PasswordInput
              {...emailRegister("confirm_password")}
              className="flex flex-col gap-3"
              containerStyle="shadow-none py-1 pr-2 rounded-xl bg-transparent"
              name="confirm_password"
            />
          </label>
          {emailErrors.confirm_password ? (
            <p className="text-sm font-semibold text-red-500">
              {emailErrors.confirm_password.message}
            </p>
          ) : (
            ""
          )}
          <Button
            type="submit"
            className="mt-2 rounded-xl bg-light-button-primaryBg text-light-button-primaryText hover:bg-light-accent-hover dark:bg-dark-button-primaryBg dark:text-dark-button-primaryText dark:hover:bg-dark-accent-hover"
          >
            ایجاد کاربر
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}