
import './App.css'
import AuthenticationLayout from './layouts/AuthenticationLayout.tsx';
import Login from './pages/Login.tsx';
import { Routes, Route } from "react-router";
import UserPanel from './pages/UserPanel.tsx';
import { ToastContainer } from "react-toastify";
import RoutesPaths from './core/routes.ts';
import Signup from './pages/Singup.tsx';
import Verify from './pages/Verify.tsx';
import ForgetPassword from './pages/ForgetPassword.tsx';
import ChangePassword from './pages/ChangePassword.tsx';
import UserPanelLayout from './layouts/UserPanelLayout.tsx';
import CreateCourse from './pages/CreateCourse.tsx';
import MangeDepartment from './pages/MangeDepartment.tsx';
import ManageUsers from './pages/ManageUsers.tsx';
function App() {


  return (
    <>
    <Routes>
      <Route  element={<AuthenticationLayout />}>
        <Route path={RoutesPaths.auth_login} element={<Login />} />
        <Route path={RoutesPaths.auth_register} element={<Signup />} />
        <Route path={RoutesPaths.auth_verify} element={<Verify />} />
        <Route path={RoutesPaths.auth_forgetPassword} element={<ForgetPassword />} />
        <Route path={RoutesPaths.auth_changePassword} element={<ChangePassword />} />
        {/* Add more routes here as needed */}
      </Route>
      <Route element={<UserPanelLayout />} >
        <Route path={RoutesPaths.user_panel} element={<UserPanel />} />
        <Route path='/create-course' element={<CreateCourse/>}/>
        <Route path='/department' element={<MangeDepartment/>}/>
        <Route path='/user-management' element={<ManageUsers/>}/>
      </Route>
      <Route path="*" element={<div>Page Not Found</div>} />
    </Routes>
      {/* You can add more routes here */}
    <ToastContainer rtl/>
    </>
  )
}

export default App
