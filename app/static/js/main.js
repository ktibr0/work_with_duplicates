$(document).ready(function() {
    $('#scan-form').submit(function(e) {
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
        $('.card-body').append('<div class="text-center mt-3"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Загрузка...</span></div><p class="mt-2">Идет сканирование директорий...</p></div>');
        $('button[type="submit"]').prop('disabled', true).html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Сканирование...');
    });
    
    $('input[type="text"]').on('blur', function() {
        if (!$(this).val().trim()) {
            $(this).val('');
        }
    });
    
    $('input[name^="directory"]').on('input', function() {
        let value = $(this).val().trim();
        if (value && !value.startsWith('//') && !value.startsWith('/')) {
            // Если путь не начинается с // или /, добавляем //
            $(this).val('//' + value);
        }
    });
    
    // Обработчик для кнопок показа/скрытия EXIF данных
    $('.exif-toggle').on('click', function() {
        let target = $(this).data('bs-target');
        if ($(target).hasClass('show')) {
            $(this).html('<i class="bi bi-info-circle"></i> Показать EXIF данные');
        } else {
            $(this).html('<i class="bi bi-info-circle-fill"></i> Скрыть EXIF данные');
        }
    });
    
    // Подсветка различающихся EXIF полей при наведении
    $('.exif-diff').hover(
        function() {
            // Получаем индекс строки в таблице
            const tagName = $(this).prev('.exif-tag').text();
            // Подсвечиваем все поля с таким же именем тега
            $(`.exif-tag`).each(function() {
                if ($(this).text() === tagName) {
                    $(this).next('.exif-value').addClass('hover-highlight');
                }
            });
        },
        function() {
            // Снимаем подсветку
            $('.hover-highlight').removeClass('hover-highlight');
        }
    );
});