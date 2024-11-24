import React, { useState } from "react";

function TextFieldInput({
    label = 'Username',
    id = 'username',
    name = 'username',
    placeholder = 'Enter your username',
    borderRadius = 'rounded-full',
    labelColor = 'text-labelGreen',
    borderColor = 'focus:ring-borderGreen',
    focusBorderColor = 'focus:ring-borderGreen',
    validationPattern = /.+/,
    errorMessage = 'This field is required',
    textColor = "text-labelGreen",
    value,
    onChange,
}) {
    const [isValid, setIsValid] = useState(true)

    const handleChange = (e) => {
        const inputValue = e.target.value;
        setIsValid(validationPattern.test(inputValue.trim()))
        onChange(inputValue);
    }

    return (
        <div className="flex flex-col space-y-2 ">
            <label htmlFor={id} className={`text-sm font-medium ${labelColor}`}>
                {label}
            </label>
            <input
                type="text"
                id={id}
                name={name}
                placeholder={placeholder}
                value={value}
                onChange={handleChange}
                className={`px-4 py-2 ${borderColor} ${borderRadius} ${textColor} shadow-sm focus:outline-none
                    focus:ring-1 ${focusBorderColor} ${!isValid ? 'border-red-700' : ''}`}
            />
            {!isValid && <p className="text-sm text-red-700">{errorMessage}</p>}
        </div>
    );
}


export default TextFieldInput;