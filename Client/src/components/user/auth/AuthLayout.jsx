import React from "react";
import AuthHeroImage from "./AuthHeroImage";
import AuthNavbar from "./AuthNavbar";

function AuthLayout({ AuthContent, link, text }) {
    return (
        <div className="flex flex-col items-center min-h-screen pb-10 bg-auth-gradient w-full">
            {/* Top Navigation Bar */}
            <AuthNavbar link={link} text={text} />

            {/* Main Content */}
            <div className="flex flex-col lg:flex-row w-[95%] lg:min-h-[600px] max-w-[1200px] rounded-xl overflow-hidden bg-login-gradient shadow-xl">
                {/* Left Section: Static Hero Image */}
                <AuthHeroImage />

                {/* Right Section: Dynamic Auth Form */}
                <div className="w-full lg:w-1/2 p-4 overflow-auto">
                    <AuthContent />
                </div>
            </div>
        </div>
    );
}

export default AuthLayout;
