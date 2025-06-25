/**
 * @method POST mobile_number,password
 */
export const USER_LOGIN_URL = "accounts/login/token/";

/**
 * @method POST refresh
 */
export const USER_REFRESH_TOKEN_URL = "accounts/login/token/refresh/";

/**
 * @method POST [Register New User] mobile_number,password,confirm_password
 * @method PUT [Verify New User with OTP code] ?mobile_number=<MOBILE>&code=<OTP>
 */
export const USER_REGISTER_URL = "accounts/user-sign-up/";

/**
 * @method GET [resend OTP] ?email=<EMAIL>
 */
export const USER_REHGISTER_OTP_RESEND = "accounts/resend-otp/";

/**
 * @method GET [sed requset for get OTP] ?email=<EMAIL>
 * @method POST [verify requset with OTP] ?email=<EMAIL>&code=<OTP>
 * @method PUT [update password] ?email=<EMAIL>&password=<PASSWORD>&confirm_password=<CONFIRM_PASSWORD>
 */
export const USER_FORGET_PASSWORD_URL = "accounts/user-forget-password/";

export const USER_CHANGE_PASSWORD_URL = "accounts/change-password-without-otp/";
/**
 * @method GET [get all users]
 * @method PUT [edit single user] id,is_active
 * @method POST [create new user] email,password,confirm_password
 */
export const ADNIM_USER_MANAGEMENT = "accounts/user-management-by-admin/";

/**
 * @method GET [show]
 * @method DELET [delete] id
 */
export const USER_MANAGEMENT = "accounts/user-management/";

/**
 * @method GET [get all profiles]
 * @method PUT [edit single profile] id,national_id
 * @method POST [create new profile] user,first_name,last_name
 */
export const ADMIN_PROFILE_MANAGEMENT = "accounts/profile-management-by-admin/";

/**
 * @method GET [show]
 * @method POST [create] user,first_name,last_name
 * @method PUT [edit] user,national_id
 */
export const USER_PROFILE_MANAGEMENT = "accounts/profile-management/";

/**
 * @method GET [get all plans]
 * @method PUT [edit single plan] ?id=<ID>  ->name,
 * @method POST [create new plan] profile,name,number_of_words,duration,is_active
 * @method DELET [delete] ?id=<ID>
 */
export const ADMIN_PLAN_MANAGEMENT = "plan/management-by-admin/";

/**
 * @method GET
 */
export const USER_GET_PLANS = "plan/show/";

/**
 * @method GET [get all transactions]
 */
export const USER_PURCHESE_HISTORY = "plan/transactions/";

/**
 * @method GET [get all transactions]
 */
export const ADMIN_ALL_PURCHESE_HISTORY = "plan/transactions-management/";

/**
 * @method GET
 */
export const USER_PURCHESE_PLAN = "plan/profile-plan/";
/**
 * @method GET [get all wallets]
 * @method POST [create new wallet] profile
 * @method DELET [delete] ?id=<ID>
 * @method PUT [edit single wallet] ?profile=<PROFILE_ID>  ->amount,
 */
export const ADMIN_WALLET_MANAGEMENT = "wallet/management-by-admin/";

/**
 * @method GET [get wallet]
 */
export const USER_GET_WALLET = "wallet/show/";

/**
 * @method GET ?amount=<AMOUNT>&profile=<PROFILE>
 */
export const USER_CHARGE_WALLET = "wallet/payment-create/";

/**
 * @method GET [get all dialogs]
 * @method PUT [edit single dialog] ?id=<ID>  ->name,
 * @method DELET [delete single dialog] ?id=<ID>
 * @method POST [create new dialog] profile,name
 */
export const DIALOG_API = "chat/dialog/";

/**
 * @method POST [chat] dialog,body,filter_size
 */
export const MESSAGE_API = "chat/message/";