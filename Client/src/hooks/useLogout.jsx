import { useDispatch, useSelector } from "react-redux"
import axiosInstance from "../axios/axiosinstance"
import { useNavigate } from "react-router-dom"
import { clearAuth } from "../redux/slices/authSlice"
import { clearProfile } from "../redux/slices/ProfileSlice"

export const useLogout = () => {
    const dispatch = useDispatch()
    const navigate = useNavigate()
    const email = useSelector((state) => state.auth.email)
    const refresh_token = localStorage.getItem("REFRESH_TOKEN")

    const logout = async () => {
        try {
            await axiosInstance.post('accounts/logout/', { refresh_token, email })
            dispatch(clearAuth())
            dispatch(clearProfile())
            localStorage.removeItem("ACCESS_TOKEN")
            localStorage.removeItem("REFRESH_TOKEN")
            navigate('/login')
        } catch (error) {
            throw new Error("Logout failed")
        }
    }

    return logout
}
