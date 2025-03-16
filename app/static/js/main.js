// app/static/js/main.js
$(document).ready(function() {
    // Валидация формы перед отправкой
    $('#scan-form').submit(function(e) {
        // Проверяем, что хотя бы одна директория указана
        let hasDirectories = false;
        for (let i = 1; i <= 4; i++) {
            if ($(`input[name="directory${i}"]`).val().trim()) {
                hasDirectories = true;
                break;
            }
        }
        
        if (!hasDirectories) {
            e.preventDefault();
            alert('Пожалуйста, укажите как минимум одну директорию для сканирования.');
            return false;
        }
        
        // Добавляем индикатор загрузки
        $('.card-body').append('<div class="text-center mt-3"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Загрузка...</span></div><p class="mt-2">Идет сканирование директорий...</p></div>');
        
        // Блокируем кнопку отправки
        $('button[type="submit"]').prop('disabled', true).html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Сканирование...');
    });
    
    // Очистка неиспользуемых полей
    $('input[type="text"]').on('blur', function() {
        if (!$(this).val().trim()) {
            $(this).val('');
        }
    });
    
    // Автоматическое заполнение Samba-пути
    $('input[name^="directory"]').on('input', function() {
        let value = $(this).val().trim();
        if (value && !value.startsWith('//') && !value.startsWith('/')) {
            // Если путь не начинается с // или /, добавляем //
            $(this).val('//' + value);
        }
    });
});