/* 拾遗阁 - 表单验证脚本 */

document.addEventListener('DOMContentLoaded', function() {
    // 初始化所有需要验证的表单
    initFormValidation();
});

/**
 * 初始化表单验证
 */
function initFormValidation() {
    // 注册表单验证
    const registerForm = document.getElementById('register-form');
    if (registerForm) {
        setupRegisterFormValidation(registerForm);
    }
    
    // 登录表单验证
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        setupLoginFormValidation(loginForm);
    }
    
    // 购物车数量输入验证
    const quantityInputs = document.querySelectorAll('.quantity-input input');
    if (quantityInputs.length > 0) {
        setupQuantityInputValidation(quantityInputs);
    }
    
    // 结算表单验证
    const checkoutForm = document.getElementById('checkout-form');
    if (checkoutForm) {
        setupCheckoutFormValidation(checkoutForm);
    }
}

/**
 * 设置注册表单验证
 * @param {HTMLFormElement} form - 注册表单元素
 */
function setupRegisterFormValidation(form) {
    // 用户名验证
    const usernameInput = form.querySelector('#username');
    if (usernameInput) {
        usernameInput.addEventListener('blur', function() {
            validateUsername(this);
        });
    }
    
    // 邮箱验证
    const emailInput = form.querySelector('#email');
    if (emailInput) {
        emailInput.addEventListener('blur', function() {
            validateEmail(this);
        });
    }
    
    // 密码验证
    const passwordInput = form.querySelector('#password');
    if (passwordInput) {
        passwordInput.addEventListener('input', function() {
            validatePassword(this);
            
            // 如果确认密码已有输入，同时验证确认密码
            const confirmInput = form.querySelector('#confirm_password');
            if (confirmInput && confirmInput.value) {
                validateConfirmPassword(confirmInput, this.value);
            }
        });
    }
    
    // 确认密码验证
    const confirmPasswordInput = form.querySelector('#confirm_password');
    if (confirmPasswordInput && passwordInput) {
        confirmPasswordInput.addEventListener('input', function() {
            validateConfirmPassword(this, passwordInput.value);
        });
    }
    
    // 表单提交验证
    form.addEventListener('submit', function(e) {
        let isValid = true;
        
        // 验证所有字段
        if (usernameInput && !validateUsername(usernameInput)) {
            isValid = false;
        }
        
        if (emailInput && !validateEmail(emailInput)) {
            isValid = false;
        }
        
        if (passwordInput && !validatePassword(passwordInput)) {
            isValid = false;
        }
        
        if (confirmPasswordInput && !validateConfirmPassword(confirmPasswordInput, passwordInput.value)) {
            isValid = false;
        }
        
        if (!isValid) {
            e.preventDefault();
        }
    });
}

/**
 * 设置登录表单验证
 * @param {HTMLFormElement} form - 登录表单元素
 */
function setupLoginFormValidation(form) {
    // 邮箱验证
    const emailInput = form.querySelector('#email');
    if (emailInput) {
        emailInput.addEventListener('blur', function() {
            validateEmail(this);
        });
    }
    
    // 密码验证(仅检查非空)
    const passwordInput = form.querySelector('#password');
    if (passwordInput) {
        passwordInput.addEventListener('blur', function() {
            validateRequired(this, '请输入密码');
        });
    }
    
    // 表单提交验证
    form.addEventListener('submit', function(e) {
        let isValid = true;
        
        // 验证邮箱
        if (emailInput && !validateEmail(emailInput)) {
            isValid = false;
        }
        
        // 验证密码非空
        if (passwordInput && !validateRequired(passwordInput, '请输入密码')) {
            isValid = false;
        }
        
        if (!isValid) {
            e.preventDefault();
        }
    });
}

/**
 * 设置商品数量输入框验证
 * @param {NodeList} inputs - 数量输入框元素集合
 */
function setupQuantityInputValidation(inputs) {
    inputs.forEach(input => {
        // 处理输入变化
        input.addEventListener('input', function() {
            let value = parseInt(this.value);
            
            // 获取最大库存量（如果有）
            const maxStock = parseInt(this.dataset.maxStock) || null;
            
            // 验证输入是数字且大于0
            if (isNaN(value) || value < 1) {
                this.value = 1;
                value = 1;
            }
            
            // 验证不超过最大库存
            if (maxStock !== null && value > maxStock) {
                this.value = maxStock;
                value = maxStock;
                showNotification(`最多可购买${maxStock}件`, 'warning');
            }
            
            // 更新总价（如果有）
            updateItemTotal(this);
        });
        
        // 增加按钮
        const increaseBtn = input.parentElement.querySelector('.quantity-increase');
        if (increaseBtn) {
            increaseBtn.addEventListener('click', function() {
                let value = parseInt(input.value);
                const maxStock = parseInt(input.dataset.maxStock) || null;
                
                if (isNaN(value)) {
                    value = 0;
                }
                
                // 检查是否超过最大库存
                if (maxStock !== null && value >= maxStock) {
                    showNotification(`最多可购买${maxStock}件`, 'warning');
                    return;
                }
                
                input.value = value + 1;
                
                // 触发input事件以更新总价
                const event = new Event('input', { bubbles: true });
                input.dispatchEvent(event);
            });
        }
        
        // 减少按钮
        const decreaseBtn = input.parentElement.querySelector('.quantity-decrease');
        if (decreaseBtn) {
            decreaseBtn.addEventListener('click', function() {
                let value = parseInt(input.value);
                
                if (isNaN(value) || value <= 1) {
                    value = 2;  // 设为2，这样减1后为1
                }
                
                input.value = value - 1;
                
                // 触发input事件以更新总价
                const event = new Event('input', { bubbles: true });
                input.dispatchEvent(event);
            });
        }
    });
}

/**
 * 设置结算表单验证
 * @param {HTMLFormElement} form - 结算表单元素
 */
function setupCheckoutFormValidation(form) {
    // 收货人姓名验证
    const nameInput = form.querySelector('#full_name');
    if (nameInput) {
        nameInput.addEventListener('blur', function() {
            validateRequired(this, '请输入收货人姓名');
        });
    }
    
    // 地址验证
    const addressInput = form.querySelector('#address');
    if (addressInput) {
        addressInput.addEventListener('blur', function() {
            validateRequired(this, '请输入收货地址');
        });
    }
    
    // 电话验证
    const phoneInput = form.querySelector('#phone');
    if (phoneInput) {
        phoneInput.addEventListener('blur', function() {
            validatePhone(this);
        });
    }
    
    // 表单提交验证
    form.addEventListener('submit', function(e) {
        let isValid = true;
        
        // 验证收货人姓名
        if (nameInput && !validateRequired(nameInput, '请输入收货人姓名')) {
            isValid = false;
        }
        
        // 验证地址
        if (addressInput && !validateRequired(addressInput, '请输入收货地址')) {
            isValid = false;
        }
        
        // 验证电话
        if (phoneInput && !validatePhone(phoneInput)) {
            isValid = false;
        }
        
        if (!isValid) {
            e.preventDefault();
        }
    });
}

/**
 * 验证用户名
 * @param {HTMLInputElement} input - 用户名输入框
 * @returns {boolean} 是否验证通过
 */
function validateUsername(input) {
    const value = input.value.trim();
    const minLength = 4;
    const maxLength = 64;
    
    // 清除之前的错误提示
    clearValidationError(input);
    
    // 检查是否为空
    if (!value) {
        setValidationError(input, '用户名不能为空');
        return false;
    }
    
    // 检查长度
    if (value.length < minLength) {
        setValidationError(input, `用户名长度不能少于${minLength}个字符`);
        return false;
    }
    
    if (value.length > maxLength) {
        setValidationError(input, `用户名长度不能超过${maxLength}个字符`);
        return false;
    }
    
    // 检查格式（字母、数字、下划线）
    const regex = /^[a-zA-Z0-9_]+$/;
    if (!regex.test(value)) {
        setValidationError(input, '用户名只能包含字母、数字和下划线');
        return false;
    }
    
    return true;
}

/**
 * 验证邮箱
 * @param {HTMLInputElement} input - 邮箱输入框
 * @returns {boolean} 是否验证通过
 */
function validateEmail(input) {
    const value = input.value.trim();
    
    // 清除之前的错误提示
    clearValidationError(input);
    
    // 检查是否为空
    if (!value) {
        setValidationError(input, '邮箱不能为空');
        return false;
    }
    
    // 检查邮箱格式
    const regex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    if (!regex.test(value)) {
        setValidationError(input, '请输入有效的邮箱地址');
        return false;
    }
    
    return true;
}

/**
 * 验证密码
 * @param {HTMLInputElement} input - 密码输入框
 * @returns {boolean} 是否验证通过
 */
function validatePassword(input) {
    const value = input.value;
    const minLength = 8;
    
    // 清除之前的错误提示
    clearValidationError(input);
    
    // 检查是否为空
    if (!value) {
        setValidationError(input, '密码不能为空');
        return false;
    }
    
    // 检查长度
    if (value.length < minLength) {
        setValidationError(input, `密码长度不能少于${minLength}个字符`);
        return false;
    }
    
    // 检查密码强度
    let strength = 0;
    
    // 包含小写字母
    if (/[a-z]/.test(value)) strength++;
    
    // 包含大写字母
    if (/[A-Z]/.test(value)) strength++;
    
    // 包含数字
    if (/[0-9]/.test(value)) strength++;
    
    // 包含特殊字符
    if (/[^a-zA-Z0-9]/.test(value)) strength++;
    
    // 设置密码强度提示
    const strengthFeedback = input.parentElement.querySelector('.password-strength');
    if (strengthFeedback) {
        strengthFeedback.classList.remove('text-danger', 'text-warning', 'text-success');
        
        if (strength <= 1) {
            strengthFeedback.textContent = '密码强度：弱';
            strengthFeedback.classList.add('text-danger');
        } else if (strength === 2) {
            strengthFeedback.textContent = '密码强度：中';
            strengthFeedback.classList.add('text-warning');
        } else {
            strengthFeedback.textContent = '密码强度：强';
            strengthFeedback.classList.add('text-success');
        }
    }
    
    // 密码至少要包含两种字符类型
    if (strength < 2) {
        setValidationError(input, '密码至少需包含大小写字母、数字或特殊字符中的两种');
        return false;
    }
    
    return true;
}

/**
 * 验证确认密码
 * @param {HTMLInputElement} input - 确认密码输入框
 * @param {string} passwordValue - 密码值
 * @returns {boolean} 是否验证通过
 */
function validateConfirmPassword(input, passwordValue) {
    const value = input.value;
    
    // 清除之前的错误提示
    clearValidationError(input);
    
    // 检查是否为空
    if (!value) {
        setValidationError(input, '请确认密码');
        return false;
    }
    
    // 检查是否与密码一致
    if (value !== passwordValue) {
        setValidationError(input, '两次输入的密码不一致');
        return false;
    }
    
    return true;
}

/**
 * 验证手机号
 * @param {HTMLInputElement} input - 手机号输入框
 * @returns {boolean} 是否验证通过
 */
function validatePhone(input) {
    const value = input.value.trim();
    
    // 清除之前的错误提示
    clearValidationError(input);
    
    // 检查是否为空
    if (!value) {
        setValidationError(input, '电话号码不能为空');
        return false;
    }
    
    // 中国大陆手机号验证
    const regex = /^1[3-9]\d{9}$/;
    if (!regex.test(value)) {
        setValidationError(input, '请输入有效的手机号码');
        return false;
    }
    
    return true;
}

/**
 * 验证必填字段
 * @param {HTMLInputElement} input - 输入框
 * @param {string} errorMessage - 错误信息
 * @returns {boolean} 是否验证通过
 */
function validateRequired(input, errorMessage) {
    const value = input.value.trim();
    
    // 清除之前的错误提示
    clearValidationError(input);
    
    // 检查是否为空
    if (!value) {
        setValidationError(input, errorMessage);
        return false;
    }
    
    return true;
}

/**
 * 设置验证错误提示
 * @param {HTMLInputElement} input - 输入框
 * @param {string} message - 错误信息
 */
function setValidationError(input, message) {
    input.classList.add('is-invalid');
    
    // 查找或创建错误提示元素
    let feedbackElement = input.parentElement.querySelector('.invalid-feedback');
    
    if (!feedbackElement) {
        feedbackElement = document.createElement('div');
        feedbackElement.className = 'invalid-feedback';
        input.parentElement.appendChild(feedbackElement);
    }
    
    feedbackElement.textContent = message;
}

/**
 * 清除验证错误提示
 * @param {HTMLInputElement} input - 输入框
 */
function clearValidationError(input) {
    input.classList.remove('is-invalid');
    
    // 移除错误提示
    const feedbackElement = input.parentElement.querySelector('.invalid-feedback');
    if (feedbackElement) {
        feedbackElement.textContent = '';
    }
}

/**
 * 更新商品单项总价
 * @param {HTMLInputElement} quantityInput - 数量输入框
 */
function updateItemTotal(quantityInput) {
    const itemRow = quantityInput.closest('.product-row');
    if (!itemRow) return;
    
    const priceElement = itemRow.querySelector('.product-price');
    const totalElement = itemRow.querySelector('.product-total');
    
    if (priceElement && totalElement) {
        const price = parseFloat(priceElement.dataset.price || priceElement.textContent.replace(/[^\d.]/g, ''));
        const quantity = parseInt(quantityInput.value);
        
        if (!isNaN(price) && !isNaN(quantity)) {
            const total = price * quantity;
            totalElement.textContent = formatPrice(total);
            
            // 如果在购物车页面，更新总价
            if (window.updateCartTotal) {
                window.updateCartTotal();
            }
        }
    }
}
