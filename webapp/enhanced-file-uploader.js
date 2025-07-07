/**
 * Enhanced File Uploader - Улучшенная загрузка файлов
 * Возможности:
 * - Drag & Drop интерфейс
 * - Превью файлов с иконками
 * - Прогресс загрузки
 * - Валидация типов и размеров
 * - Сжатие изображений
 * - Пакетная загрузка
 */

class EnhancedFileUploader {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.options = {
            maxFiles: options.maxFiles || 5,
            maxFileSize: options.maxFileSize || 10 * 1024 * 1024, // 10MB
            allowedTypes: options.allowedTypes || ['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'],
            compressionQuality: options.compressionQuality || 0.8,
            showProgress: options.showProgress !== false,
            enableDragDrop: options.enableDragDrop !== false,
            ...options
        };
        
        this.files = [];
        this.uploadQueue = [];
        this.isUploading = false;
        
        this.init();
    }

    /**
     * Инициализация компонента
     */
    init() {
        this.createUploadZone();
        this.setupEventListeners();
    }

    /**
     * Создание зоны загрузки
     */
    createUploadZone() {
        this.container.innerHTML = `
            <div class="file-upload-zone" id="upload-zone">
                <div class="upload-content">
                    <div class="upload-icon text-4xl mb-4">📎</div>
                    <h3 class="text-lg font-semibold mb-2">Прикрепите документы</h3>
                    <p class="text-gray-600 mb-4">
                        Перетащите файлы сюда или 
                        <button type="button" class="text-blue-600 hover:text-blue-800 font-medium underline" id="browse-files">
                            выберите файлы
                        </button>
                    </p>
                    <div class="text-sm text-gray-500">
                        <p>Поддерживаемые форматы: ${this.options.allowedTypes.join(', ').toUpperCase()}</p>
                        <p>Максимальный размер: ${this.formatFileSize(this.options.maxFileSize)}</p>
                        <p>Максимум файлов: ${this.options.maxFiles}</p>
                    </div>
                </div>
                <input type="file" id="file-input" multiple accept="${this.getAcceptString()}" class="hidden">
            </div>
            <div id="file-list" class="mt-4 space-y-3">
                <!-- Список файлов будет здесь -->
            </div>
            <div id="upload-progress" class="mt-4 hidden">
                <div class="flex items-center justify-between mb-2">
                    <span class="text-sm font-medium">Загрузка файлов...</span>
                    <span class="text-sm text-gray-500" id="progress-text">0%</span>
                </div>
                <div class="upload-progress">
                    <div class="upload-progress-bar" id="progress-bar" style="width: 0%"></div>
                </div>
            </div>
        `;
        
        this.uploadZone = this.container.querySelector('#upload-zone');
        this.fileInput = this.container.querySelector('#file-input');
        this.fileList = this.container.querySelector('#file-list');
        this.progressContainer = this.container.querySelector('#upload-progress');
        this.progressBar = this.container.querySelector('#progress-bar');
        this.progressText = this.container.querySelector('#progress-text');
    }

    /**
     * Настройка обработчиков событий
     */
    setupEventListeners() {
        // Обработчики для drag & drop
        if (this.options.enableDragDrop) {
            this.uploadZone.addEventListener('dragover', this.handleDragOver.bind(this));
            this.uploadZone.addEventListener('dragleave', this.handleDragLeave.bind(this));
            this.uploadZone.addEventListener('drop', this.handleDrop.bind(this));
        }

        // Клик по зоне загрузки
        this.container.querySelector('#browse-files').addEventListener('click', () => {
            this.fileInput.click();
        });

        // Выбор файлов через input
        this.fileInput.addEventListener('change', (e) => {
            this.handleFiles(Array.from(e.target.files));
        });

        // Предотвращение drag & drop на всей странице
        document.addEventListener('dragover', (e) => e.preventDefault());
        document.addEventListener('drop', (e) => e.preventDefault());
    }

    /**
     * Обработка dragover
     */
    handleDragOver(e) {
        e.preventDefault();
        this.uploadZone.classList.add('dragover');
    }

    /**
     * Обработка dragleave
     */
    handleDragLeave(e) {
        e.preventDefault();
        if (!this.uploadZone.contains(e.relatedTarget)) {
            this.uploadZone.classList.remove('dragover');
        }
    }

    /**
     * Обработка drop
     */
    handleDrop(e) {
        e.preventDefault();
        this.uploadZone.classList.remove('dragover');
        
        const files = Array.from(e.dataTransfer.files);
        this.handleFiles(files);
    }

    /**
     * Обработка файлов
     */
    async handleFiles(files) {
        // Проверяем лимит файлов
        if (this.files.length + files.length > this.options.maxFiles) {
            this.showError(`Максимум ${this.options.maxFiles} файлов`);
            return;
        }

        const validFiles = [];
        
        for (const file of files) {
            const validation = this.validateFile(file);
            if (validation.valid) {
                const processedFile = await this.processFile(file);
                validFiles.push(processedFile);
            } else {
                this.showError(`${file.name}: ${validation.error}`);
            }
        }

        // Добавляем валидные файлы
        validFiles.forEach(file => {
            this.files.push(file);
            this.renderFilePreview(file);
        });

        // Обновляем состояние формы
        this.updateFormData();
        
        // Скрываем зону загрузки если достигнут лимит
        if (this.files.length >= this.options.maxFiles) {
            this.uploadZone.style.display = 'none';
        }
    }

    /**
     * Валидация файла
     */
    validateFile(file) {
        // Проверка размера
        if (file.size > this.options.maxFileSize) {
            return {
                valid: false,
                error: `Размер файла превышает ${this.formatFileSize(this.options.maxFileSize)}`
            };
        }

        // Проверка типа
        const extension = file.name.split('.').pop().toLowerCase();
        if (!this.options.allowedTypes.includes(extension)) {
            return {
                valid: false,
                error: `Неподдерживаемый формат файла (${extension})`
            };
        }

        return { valid: true };
    }

    /**
     * Обработка файла (сжатие изображений, преобразование в base64)
     */
    async processFile(file) {
        const fileData = {
            id: this.generateFileId(),
            name: file.name,
            size: file.size,
            type: file.type,
            extension: file.name.split('.').pop().toLowerCase(),
            originalFile: file,
            data: null,
            thumbnail: null,
            uploadProgress: 0
        };

        // Если это изображение, создаем превью и сжимаем
        if (this.isImage(file)) {
            fileData.thumbnail = await this.createImageThumbnail(file);
            
            // Сжимаем если размер больше 1MB
            if (file.size > 1024 * 1024) {
                const compressedFile = await this.compressImage(file);
                fileData.data = await this.fileToBase64(compressedFile);
                fileData.size = compressedFile.size;
            } else {
                fileData.data = await this.fileToBase64(file);
            }
        } else {
            fileData.data = await this.fileToBase64(file);
        }

        return fileData;
    }

    /**
     * Создание превью изображения
     */
    async createImageThumbnail(file) {
        return new Promise((resolve) => {
            const reader = new FileReader();
            reader.onload = (e) => {
                const img = new Image();
                img.onload = () => {
                    const canvas = document.createElement('canvas');
                    const ctx = canvas.getContext('2d');
                    
                    // Размеры превью
                    const maxWidth = 100;
                    const maxHeight = 100;
                    
                    let { width, height } = img;
                    
                    // Пропорциональное изменение размера
                    if (width > height) {
                        if (width > maxWidth) {
                            height = (height * maxWidth) / width;
                            width = maxWidth;
                        }
                    } else {
                        if (height > maxHeight) {
                            width = (width * maxHeight) / height;
                            height = maxHeight;
                        }
                    }
                    
                    canvas.width = width;
                    canvas.height = height;
                    
                    ctx.drawImage(img, 0, 0, width, height);
                    resolve(canvas.toDataURL('image/jpeg', 0.7));
                };
                img.src = e.target.result;
            };
            reader.readAsDataURL(file);
        });
    }

    /**
     * Сжатие изображения
     */
    async compressImage(file) {
        return new Promise((resolve) => {
            const reader = new FileReader();
            reader.onload = (e) => {
                const img = new Image();
                img.onload = () => {
                    const canvas = document.createElement('canvas');
                    const ctx = canvas.getContext('2d');
                    
                    // Уменьшаем размеры для сжатия
                    const maxWidth = 1200;
                    const maxHeight = 1200;
                    
                    let { width, height } = img;
                    
                    if (width > height) {
                        if (width > maxWidth) {
                            height = (height * maxWidth) / width;
                            width = maxWidth;
                        }
                    } else {
                        if (height > maxHeight) {
                            width = (width * maxHeight) / height;
                            height = maxHeight;
                        }
                    }
                    
                    canvas.width = width;
                    canvas.height = height;
                    
                    ctx.drawImage(img, 0, 0, width, height);
                    
                    canvas.toBlob(resolve, 'image/jpeg', this.options.compressionQuality);
                };
                img.src = e.target.result;
            };
            reader.readAsDataURL(file);
        });
    }

    /**
     * Преобразование файла в base64
     */
    async fileToBase64(file) {
        return new Promise((resolve) => {
            const reader = new FileReader();
            reader.onload = (e) => {
                // Убираем префикс data:mime;base64,
                const base64 = e.target.result.split(',')[1];
                resolve(base64);
            };
            reader.readAsDataURL(file);
        });
    }

    /**
     * Отображение превью файла
     */
    renderFilePreview(fileData) {
        const fileElement = document.createElement('div');
        fileElement.className = 'file-preview flex items-center justify-between p-3 bg-white border rounded-lg';
        fileElement.dataset.fileId = fileData.id;
        
        fileElement.innerHTML = `
            <div class="flex items-center space-x-3">
                <div class="file-icon ${fileData.extension}" title="${fileData.type}">
                    ${this.getFileIcon(fileData)}
                </div>
                <div class="flex-1 min-w-0">
                    <p class="text-sm font-medium text-gray-900 truncate">${fileData.name}</p>
                    <p class="text-sm text-gray-500">${this.formatFileSize(fileData.size)}</p>
                </div>
            </div>
            <div class="flex items-center space-x-2">
                ${fileData.thumbnail ? `<img src="${fileData.thumbnail}" alt="Preview" class="w-12 h-12 object-cover rounded">` : ''}
                <button type="button" class="text-red-500 hover:text-red-700 p-1" onclick="enhancedFileUploader.removeFile('${fileData.id}')">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
        `;
        
        this.fileList.appendChild(fileElement);
        
        // Анимация появления
        fileElement.style.opacity = '0';
        fileElement.style.transform = 'translateY(20px)';
        
        requestAnimationFrame(() => {
            fileElement.style.transition = 'all 0.3s ease';
            fileElement.style.opacity = '1';
            fileElement.style.transform = 'translateY(0)';
        });
    }

    /**
     * Получение иконки файла
     */
    getFileIcon(fileData) {
        if (fileData.thumbnail) {
            return `<img src="${fileData.thumbnail}" alt="Preview" class="w-6 h-6 object-cover rounded">`;
        }
        
        const iconMap = {
            pdf: '📄',
            doc: '📝',
            docx: '📝',
            jpg: '🖼️',
            jpeg: '🖼️',
            png: '🖼️'
        };
        
        return iconMap[fileData.extension] || '📄';
    }

    /**
     * Удаление файла
     */
    removeFile(fileId) {
        // Находим и удаляем файл из массива
        this.files = this.files.filter(file => file.id !== fileId);
        
        // Удаляем элемент из DOM с анимацией
        const fileElement = this.fileList.querySelector(`[data-file-id="${fileId}"]`);
        if (fileElement) {
            fileElement.style.transition = 'all 0.3s ease';
            fileElement.style.opacity = '0';
            fileElement.style.transform = 'translateX(-100%)';
            
            setTimeout(() => {
                fileElement.remove();
            }, 300);
        }
        
        // Показываем зону загрузки если есть место
        if (this.files.length < this.options.maxFiles) {
            this.uploadZone.style.display = 'block';
        }
        
        // Обновляем данные формы
        this.updateFormData();
    }

    /**
     * Обновление данных формы
     */
    updateFormData() {
        const filesData = this.files.map(file => ({
            name: file.name,
            type: file.type,
            size: file.size,
            data: file.data
        }));
        
        // Обновляем глобальные данные формы
        if (window.enhancedFormManager) {
            window.enhancedFormManager.updateFormData('files', filesData);
        }
        
        // Вызываем callback если установлен
        if (this.options.onChange) {
            this.options.onChange(filesData);
        }
    }

    /**
     * Вспомогательные методы
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    isImage(file) {
        return file.type.startsWith('image/');
    }

    generateFileId() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2, 9);
    }

    getAcceptString() {
        const mimeTypes = {
            pdf: 'application/pdf',
            doc: 'application/msword',
            docx: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            jpg: 'image/jpeg',
            jpeg: 'image/jpeg',
            png: 'image/png'
        };
        
        return this.options.allowedTypes
            .map(type => mimeTypes[type] || `.${type}`)
            .join(',');
    }

    showError(message) {
        // Создаем уведомление об ошибке
        const notification = document.createElement('div');
        notification.className = 'notification error fixed top-4 right-4 px-4 py-2 rounded shadow-lg text-white z-50';
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.opacity = '0';
            setTimeout(() => notification.remove(), 300);
        }, 4000);
    }

    /**
     * Получение всех файлов
     */
    getFiles() {
        return this.files.map(file => ({
            name: file.name,
            type: file.type,
            size: file.size,
            data: file.data
        }));
    }

    /**
     * Очистка всех файлов
     */
    clearFiles() {
        this.files = [];
        this.fileList.innerHTML = '';
        this.uploadZone.style.display = 'block';
        this.updateFormData();
    }

    /**
     * Установка файлов (для восстановления состояния)
     */
    setFiles(files) {
        this.clearFiles();
        files.forEach(fileData => {
            this.files.push(fileData);
            this.renderFilePreview(fileData);
        });
        this.updateFormData();
    }
}

// Глобальная инициализация
let enhancedFileUploader;

document.addEventListener('DOMContentLoaded', () => {
    // Заменяем стандартную загрузку файлов на улучшенную
    const fileListContainer = document.getElementById('file-list');
    if (fileListContainer) {
        // Создаем контейнер для нового uploader
        const uploaderContainer = document.createElement('div');
        uploaderContainer.id = 'enhanced-file-uploader';
        
        // Вставляем перед существующим элементом
        fileListContainer.parentNode.insertBefore(uploaderContainer, fileListContainer);
        
        // Скрываем старый элемент
        fileListContainer.style.display = 'none';
        
        // Инициализируем новый uploader
        enhancedFileUploader = new EnhancedFileUploader('enhanced-file-uploader');
        window.enhancedFileUploader = enhancedFileUploader;
    }
});

// Экспорт для использования в других модулях
window.EnhancedFileUploader = EnhancedFileUploader; 