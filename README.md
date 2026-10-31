# StegoCrypto

## Зависимости

Python 3.10+.

pip install -r requirements.txt

(numpy, pillow, pycryptodome, scipy, scikit-image, matplotlib)

## Запуск

Все команды запускаются из папки StegoCrypto.

### Встраивание

python src/stego.py embed -i <cover.png> -o <stego.png> (-m "текст" | -f файл.txt) [--mode plain|encrypted|random] [-p пароль]

Параметры:

- -i - исходная картинка;
- -o - куда сохранить результат (всегда PNG);
- -m - текст сообщения, или -f - файл, из которого брать данные;
- --mode - режим:
  - plain - открытый текст, последовательные позиции (по умолчанию);
  - encrypted - AES-256-GCM, последовательные позиции;
  - random - AES-256-GCM, псевдослучайные позиции;
- -p - пароль (обязателен для encrypted и random).

Если сообщение не помещается в картинку, программа выводит ошибку и завершается с кодом 1.

### Извлечение

python src/stego.py extract -i <stego.png> [--mode plain|encrypted|random] [-p пароль] [-o out.txt]

Без -o текст печатается в консоль.

## Примеры

Обычный LSB:

python src/stego.py embed -i ../gradient.png -o imgs/test_plain.png -m "Привет, мир!"

python src/stego.py extract -i imgs/test_plain.png

Гибридный режим (шифрование + LSB):

python src/stego.py embed -i ../gradient.png -o imgs/test_enc.png -m "Секрет" --mode encrypted -p qwerty

python src/stego.py embed -i ../gradient.png -o imgs/test_rnd.png -m "Секрет" --mode random -p qwerty

Извлечение и расшифрование:

python src/stego.py extract -i imgs/test_enc.png --mode encrypted -p qwerty

python src/stego.py extract -i imgs/test_rnd.png --mode random -p qwerty

С неправильным паролем будет Ошибка: MAC check failed (для random - ошибка длины, потому что не совпадёт порядок позиций).

## Эксперимент

python src/experiment.py

Берёт картинки из папки лабораторной (../gradient.png, ../my_pic.png, ../checkerboard.png, ../noise_texture.png), встраивает 1% и 5% от вместимости всеми тремя способами и сохраняет:

- imgs/ - cover и stego-картинки (основной пример - gradient, 5%; остальные в подпапках);
- results/metrics.csv - все метрики;
- results/difference.png, results/histogram.png - графики.

Соль и nonce случайные, поэтому у зашифрованных вариантов цифры немного отличаются от запуска к запуску.
