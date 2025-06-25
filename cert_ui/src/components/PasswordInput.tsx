import React, { forwardRef } from "react";
import { FaRegEye, FaRegEyeSlash } from "react-icons/fa";

import { cn } from "@/lib/utils";

interface Props extends React.InputHTMLAttributes<HTMLInputElement> {
  passwordLabel?: string;
  placeholder?: string;
  name?: string;
  className?: string;
  value?: string;
  containerStyle?: string;
  autoComplete?: string;
  disabled?: boolean;
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
  passwordRef?: React.Ref<HTMLInputElement>;
}

const PasswordInput = forwardRef<HTMLInputElement, Props>(
  (
    {
      passwordLabel,
      placeholder,
      name = "password",
      className = "flex items-center gap-2",
      containerStyle,
      autoComplete,
      value,
      onChange,
      disabled,
    },
    ref,
  ) => {
    const [show, setShow] = React.useState(false);

    return (
      <label htmlFor={name} className={`${className}`}>
        {passwordLabel}
        <div
          className={cn(
            "flex w-full flex-row-reverse items-center gap-2 rounded-md border-2 border-light-border-primary bg-transparent pr-3 transition-colors duration-300 placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50 dark:border-dark-border-primary",
            {
              "focus-within:border-light-border-focus active:border-light-border-focus dark:focus-within:border-dark-border-focus dark:active:border-dark-border-focus":
                !disabled,
            },
            containerStyle,
          )}
        >
          <input
            ref={ref}
            placeholder={placeholder}
            value={value}
            onChange={onChange}
            autoComplete={autoComplete}
            className="w-full bg-transparent px-2 text-light-text-primary outline-none autocomplete-clear placeholder:text-right dark:text-dark-text-primary"
            style={{ direction: "ltr" }}
            type={show ? "text" : "password"}
            id={name}
            disabled={disabled}
            name={name}
          />
          <span
            className={cn(
              "text-light-text-primary dark:text-dark-text-primary",
              { "cursor-pointer": !disabled },
            )}
            onClick={() => {
              if (!disabled) setShow(!show);
            }}
          >
            {show ? <FaRegEye /> : <FaRegEyeSlash />}
          </span>
        </div>
      </label>
    );
  },
);

export default PasswordInput;