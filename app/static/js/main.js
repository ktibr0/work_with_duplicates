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
            $(this).val('//' + value);
        }
    });
    $('.exif-toggle').on('click', function() {
        let target = $(this).data('bs-target');
        if ($(target).hasClass('show')) {
            $(this).html('<i class="bi bi-info-circle"></i> Показать EXIF данные');
        } else {
            $(this).html('<i class="bi bi-info-circle-fill"></i> Скрыть EXIF данные');
        }
    });
    $('.exif-diff').hover(
        function() {
            const tagName = $(this).prev('.exif-tag').text();
            $(`.exif-tag`).each(function() {
                if ($(this).text() === tagName) {
                    $(this).next('.exif-value').addClass('hover-highlight');
                }
            });
        },
        function() {
            $('.hover-highlight').removeClass('hover-highlight');
        }
    );
});