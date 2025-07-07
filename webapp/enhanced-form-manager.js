/**
 * Enhanced Form Manager - UX улучшения для формы заявки
 * Возможности:
 * - Реактивная валидация в реальном времени
 * - Автосохранение прогресса в localStorage
 * - Умные подсказки и предложения
 * - Анимированные переходы между шагами
 * - Восстановление данных при перезагрузке
 */

class EnhancedFormManager {
    constructor() {
        this.STORAGE_KEY = 'yr_app_form_data';
        this.AUTO_SAVE_INTERVAL = 2000; // автосохранение каждые 2 сек
        this.validators = this.initValidators();
        this.autoSaveTimer = null;
        this.validationCache = new Map();
        
        // Состояние формы
        this.formState = {
            currentStep: 1,
            lastSaved: null,
            isValid: false,
            errors: {},
            data: this.loadSavedData() || {
                category_id: null,
                category_name: "",
                subcategory: "",
                description: "",
                name: "",
                phone: "",
                email: "",
                contact_method: "",
                contact_time: "any",
                files: [],
                tg_user_id: window.tg?.initDataUnsafe?.user?.id || null,
                utm_source: new URLSearchParams(window.tg?.initData || '').get('start_param') || null
            }
        };

        this.init();
    }

    /**
     * Инициализация валидаторов для каждого поля
     */
    initValidators() {
        return {
            category_id: {
                required: true,
                validate: (value) => {
                    if (!value) return { valid: false, message: "Выберите категорию услуг" };
                    return { valid: true };
                }
            },
            subcategory: {
                required: false,
                minLength: 3,
                validate: (value, formData) => {
                    if (value && value.length < 3) {
                        return { valid: false, message: "Минимум 3 символа" };
                    }
                    return { valid: true };
                }
            },
            description: {
                required: true,
                minLength: 10,
                maxLength: 2000,
                validate: (value) => {
                    if (!value || value.trim().length === 0) {
                        return { valid: false, message: "Опишите вашу проблему" };
                    }
                    if (value.length < 10) {
                        return { valid: false, message: "Описание слишком короткое (минимум 10 символов)" };
                    }
                    if (value.length > 2000) {
                        return { valid: false, message: "Описание слишком длинное (максимум 2000 символов)" };
                    }
                    return { valid: true };
                }
            },
            name: {
                required: true,
                pattern: /^[а-яё\s\-]+$/i,
                validate: (value) => {
                    if (!value || value.trim().length === 0) {
                        return { valid: false, message: "Введите ваше имя" };
                    }
                    if (value.trim().length < 2) {
                        return { valid: false, message: "Имя слишком короткое" };
                    }
                    if (!/^[а-яё\s\-]+$/i.test(value)) {
                        return { valid: false, message: "Имя может содержать только русские буквы" };
                    }
                    return { valid: true };
                }
            },
            phone: {
                required: true,
                pattern: /^[\+]?[7|8][\s\-]?\(?[489][0-9]{2}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{2}[\s\-]?[0-9]{2}$/,
                validate: (value) => {
                    if (!value || value.trim().length === 0) {
                        return { valid: false, message: "Введите номер телефона" };
                    }
                    
                    // Убираем все нецифровые символы кроме +
                    const cleanPhone = value.replace(/[^\d+]/g, '');
                    
                    if (cleanPhone.length < 11) {
                        return { valid: false, message: "Номер телефона слишком короткий" };
                    }
                    
                    if (!this.validators.phone.pattern.test(value)) {
                        return { valid: false, message: "Неверный формат номера (например: +7 999 123-45-67)" };
                    }
                    
                    return { valid: true };
                }
            },
            email: {
                required: false,
                pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
                validate: (value) => {
                    if (!value || value.trim().length === 0) {
                        return { valid: true }; // email необязательный
                    }
                    if (!this.validators.email.pattern.test(value)) {
                        return { valid: false, message: "Неверный формат email" };
                    }
                    return { valid: true };
                }
            },
            contact_method: {
                required: true,
                validate: (value) => {
                    if (!value) {
                        return { valid: false, message: "Выберите способ связи" };
                    }
                    return { valid: true };
                }
            }
        };
    }

    /**
     * Инициализация компонента
     */
    init() {
        this.setupEventListeners();
        this.restoreFormData();
        this.startAutoSave();
        
        // Показываем уведомление о восстановлении данных
        if (this.formState.lastSaved) {
            this.showNotification(
                `Восстановлены данные от ${new Date(this.formState.lastSaved).toLocaleString()}`,
                'info',
                3000
            );
        }
    }

    /**
     * Настройка обработчиков событий
     */
    setupEventListeners() {
        // Валидация в реальном времени для всех полей
        const inputs = document.querySelectorAll('input, textarea, select');
        inputs.forEach(input => {
            // Убираем старые обработчики если есть
            input.removeEventListener('input', this.handleInputChange.bind(this));
            input.removeEventListener('blur', this.handleInputBlur.bind(this));
            
            // Добавляем новые
            input.addEventListener('input', this.handleInputChange.bind(this));
            input.addEventListener('blur', this.handleInputBlur.bind(this));
        });

        // Обработчик для выбора категории
        document.addEventListener('categorySelected', (e) => {
            this.updateFormData('category_id', e.detail.categoryId);
            this.updateFormData('category_name', e.detail.categoryName);
            this.validateField('category_id');
        });

        // Сохранение при закрытии страницы
        window.addEventListener('beforeunload', () => {
            this.saveFormData();
        });

        // Восстановление фокуса при возврате к странице
        window.addEventListener('pageshow', () => {
            this.restoreFormData();
        });
    }

    /**
     * Обработчик изменения полей ввода
     */
    handleInputChange(event) {
        const field = event.target.id || event.target.name;
        const value = event.target.value;
        
        if (field) {
            this.updateFormData(field, value);
            
            // Валидация с задержкой для лучшего UX
            clearTimeout(this.validationTimer);
            this.validationTimer = setTimeout(() => {
                this.validateField(field);
            }, 300);
        }
    }

    /**
     * Обработчик потери фокуса
     */
    handleInputBlur(event) {
        const field = event.target.id || event.target.name;
        if (field) {
            this.validateField(field);
        }
    }

    /**
     * Валидация конкретного поля
     */
    validateField(fieldName, showFeedback = true) {
        const validator = this.validators[fieldName];
        if (!validator) return { valid: true };

        const value = this.formState.data[fieldName];
        const result = validator.validate(value, this.formState.data);
        
        // Обновляем состояние ошибок
        if (result.valid) {
            delete this.formState.errors[fieldName];
        } else {
            this.formState.errors[fieldName] = result.message;
        }

        // Показываем визуальную обратную связь
        if (showFeedback) {
            this.showFieldFeedback(fieldName, result);
        }

        return result;
    }

    /**
     * Валидация всей формы или текущего шага
     */
    validateCurrentStep() {
        const stepFields = this.getStepFields(this.formState.currentStep);
        let isValid = true;
        
        stepFields.forEach(fieldName => {
            const result = this.validateField(fieldName, true);
            if (!result.valid) {
                isValid = false;
            }
        });

        this.formState.isValid = isValid;
        return isValid;
    }

    /**
     * Получение полей для конкретного шага
     */
    getStepFields(step) {
        const stepFieldsMap = {
            1: ['category_id'],
            2: ['subcategory', 'description'],
            3: ['name', 'phone', 'email', 'contact_method'],
            4: [] // шаг подтверждения
        };
        return stepFieldsMap[step] || [];
    }

    /**
     * Показ визуальной обратной связи для поля
     */
    showFieldFeedback(fieldName, result) {
        const element = document.getElementById(fieldName);
        if (!element) return;

        const container = element.closest('.form-field') || element.parentElement;
        
        // Убираем старые классы
        element.classList.remove('border-red-500', 'border-green-500', 'border-gray-300');
        
        // Убираем старые сообщения об ошибках
        const oldError = container.querySelector('.field-error');
        if (oldError) oldError.remove();
        
        const oldSuccess = container.querySelector('.field-success');
        if (oldSuccess) oldSuccess.remove();

        if (result.valid) {
            // Успешная валидация
            element.classList.add('border-green-500');
            
            // Добавляем иконку успеха
            const successIcon = document.createElement('div');
            successIcon.className = 'field-success absolute right-3 top-1/2 transform -translate-y-1/2 text-green-500';
            successIcon.innerHTML = '✓';
            if (container.style.position !== 'relative') {
                container.style.position = 'relative';
            }
            container.appendChild(successIcon);
            
        } else {
            // Ошибка валидации
            element.classList.add('border-red-500');
            
            // Добавляем сообщение об ошибке
            const errorDiv = document.createElement('div');
            errorDiv.className = 'field-error text-red-500 text-sm mt-1 animate-fade-in';
            errorDiv.textContent = result.message;
            container.appendChild(errorDiv);
            
            // Небольшая анимация "встряхивания"
            element.style.animation = 'shake 0.3s ease-in-out';
            setTimeout(() => {
                element.style.animation = '';
            }, 300);
        }
    }

    /**
     * Обновление данных формы
     */
    updateFormData(field, value) {
        this.formState.data[field] = value;
        this.triggerAutoSave();
    }

    /**
     * Запуск автосохранения
     */
    triggerAutoSave() {
        clearTimeout(this.autoSaveTimer);
        this.autoSaveTimer = setTimeout(() => {
            this.saveFormData();
        }, this.AUTO_SAVE_INTERVAL);
    }

    /**
     * Сохранение данных в localStorage
     */
    saveFormData() {
        try {
            const dataToSave = {
                ...this.formState,
                lastSaved: new Date().toISOString()
            };
            localStorage.setItem(this.STORAGE_KEY, JSON.stringify(dataToSave));
            this.formState.lastSaved = dataToSave.lastSaved;
            
            // Показываем уведомление о сохранении
            this.showSaveIndicator();
        } catch (error) {
            console.warn('Не удалось сохранить данные формы:', error);
        }
    }

    /**
     * Загрузка сохраненных данных
     */
    loadSavedData() {
        try {
            const saved = localStorage.getItem(this.STORAGE_KEY);
            if (saved) {
                const parsedData = JSON.parse(saved);
                // Проверяем, не устарели ли данные (более 24 часов)
                const savedTime = new Date(parsedData.lastSaved);
                const now = new Date();
                const hoursDiff = (now - savedTime) / (1000 * 60 * 60);
                
                if (hoursDiff < 24) {
                    return parsedData;
                } else {
                    // Удаляем устаревшие данные
                    localStorage.removeItem(this.STORAGE_KEY);
                }
            }
        } catch (error) {
            console.warn('Не удалось загрузить сохраненные данные:', error);
        }
        return null;
    }

    /**
     * Восстановление данных в форме
     */
    restoreFormData() {
        if (!this.formState.data) return;

        // Восстанавливаем значения полей
        Object.keys(this.formState.data).forEach(fieldName => {
            const element = document.getElementById(fieldName);
            if (element && this.formState.data[fieldName]) {
                element.value = this.formState.data[fieldName];
            }
        });

        // Восстанавливаем выбранную категорию
        if (this.formState.data.category_id) {
            const categoryCard = document.querySelector(`[data-id="${this.formState.data.category_id}"]`);
            if (categoryCard) {
                categoryCard.classList.add('selected');
            }
        }
    }

    /**
     * Показ индикатора сохранения
     */
    showSaveIndicator() {
        const indicator = document.getElementById('save-indicator') || this.createSaveIndicator();
        indicator.style.opacity = '1';
        indicator.textContent = '✓ Сохранено';
        
        setTimeout(() => {
            indicator.style.opacity = '0';
        }, 1500);
    }

    /**
     * Создание индикатора сохранения
     */
    createSaveIndicator() {
        const indicator = document.createElement('div');
        indicator.id = 'save-indicator';
        indicator.className = 'fixed top-4 right-4 bg-green-500 text-white px-3 py-1 rounded text-sm transition-opacity opacity-0 z-50';
        document.body.appendChild(indicator);
        return indicator;
    }

    /**
     * Показ уведомлений
     */
    showNotification(message, type = 'info', duration = 3000) {
        const notification = document.createElement('div');
        notification.className = `fixed top-4 left-1/2 transform -translate-x-1/2 px-4 py-2 rounded shadow-lg text-white z-50 transition-all duration-300 ${this.getNotificationClass(type)}`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        // Анимация появления
        setTimeout(() => notification.style.transform = 'translate(-50%, 0)', 100);
        
        // Автоудаление
        setTimeout(() => {
            notification.style.transform = 'translate(-50%, -100%)';
            notification.style.opacity = '0';
            setTimeout(() => notification.remove(), 300);
        }, duration);
    }

    /**
     * Получение CSS класса для уведомления
     */
    getNotificationClass(type) {
        const classes = {
            'info': 'bg-blue-500',
            'success': 'bg-green-500',
            'warning': 'bg-yellow-500',
            'error': 'bg-red-500'
        };
        return classes[type] || classes.info;
    }

    /**
     * Очистка сохраненных данных
     */
    clearSavedData() {
        localStorage.removeItem(this.STORAGE_KEY);
        this.formState.lastSaved = null;
    }

    /**
     * Старт автосохранения
     */
    startAutoSave() {
        // Автосохранение каждые 30 секунд
        setInterval(() => {
            if (Object.keys(this.formState.data).some(key => this.formState.data[key])) {
                this.saveFormData();
            }
        }, 30000);
    }

    /**
     * Получение текущих данных формы
     */
    getFormData() {
        return { ...this.formState.data };
    }

    /**
     * Проверка, есть ли несохраненные изменения
     */
    hasUnsavedChanges() {
        if (!this.formState.lastSaved) return true;
        
        // Сравниваем текущие данные с сохраненными
        const saved = this.loadSavedData();
        return JSON.stringify(this.formState.data) !== JSON.stringify(saved?.data || {});
    }
}

// Глобальная инициализация при загрузке страницы
let enhancedFormManager;

document.addEventListener('DOMContentLoaded', () => {
    enhancedFormManager = new EnhancedFormManager();
    window.enhancedFormManager = enhancedFormManager; // Для отладки
});

// Экспорт для использования в других модулях
window.EnhancedFormManager = EnhancedFormManager; 