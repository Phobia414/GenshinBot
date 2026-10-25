# characters.py
# Все персонажи с картинками.

REGIONS = {
    "mondstadt": "🍃 Мондштадт",
    "liyue":     "🪨 Ли Юэ",
    "inazuma":   "⚡ Инадзума",
    "sumeru":    "🌿 Сумеру",
    "fontaine":  "💧 Фонтейн",
    "natlan":    "🔥 Натлан",
    "nodkrai":   "🌙 Нод-Край",
    "snezhnaya": "❄️ Снежная",
    "other":     "✨ Другие",
}

CHARACTERS = {
    # ===== Мондштадт =====
    "Альбедо":  {"region": "mondstadt", "image": "https://i.pinimg.com/originals/d2/28/78/d228782597f1a045101c9bca1e071d1e.jpg"},
    "Барбара":  {"region": "mondstadt", "image": "https://avatars.mds.yandex.net/i?id=4c1010dc84511d676b17cec4540907cb_l-4599697-images-thumbs&n=13"},
    "Беннет":   {"region": "mondstadt", "image": "https://i.pinimg.com/originals/ab/c6/ea/abc6ea8e6a4866e2273f9f1a02839a5c.jpg"},
    "Венти":    {"region": "mondstadt", "image": "https://avatars.mds.yandex.net/i?id=9e1f907778d2b5cbfcc7875d6e59d096_l-5875818-images-thumbs&n=13"},
    "Джинн":    {"region": "mondstadt", "image": "https://avatars.mds.yandex.net/i?id=64ab111fb53e36c0f532b4523b955dec_l-18180755-images-thumbs&n=13"},
    "Дилюк":    {"region": "mondstadt", "image": "https://i.pinimg.com/originals/64/64/2b/64642b6796c0f06e6bdfa9075d0c4ee4.jpg"},
    "Диона":    {"region": "mondstadt", "image": "https://avatars.mds.yandex.net/i?id=f2644b4872b081b3c046799ed3644c63_l-4825588-images-thumbs&n=13"},
    "Кли":      {"region": "mondstadt", "image": "https://i.pinimg.com/originals/ac/75/56/ac755687ba417d2f3ccd16d98826dcc4.png?nii=t"},
    "Кэйа":     {"region": "mondstadt", "image": "https://i.pinimg.com/originals/43/c3/e0/43c3e013573f696c998ce0831decab8a.jpg"},
    "Лиза":     {"region": "mondstadt", "image": "https://avatars.mds.yandex.net/i?id=77af76d7d78c333adcd219a1472f1c0c_l-5277647-images-thumbs&n=13"},
    "Мика":     {"region": "mondstadt", "image": "https://i.pinimg.com/originals/b1/76/bc/b176bc2231e24da828e289e1712cf715.jpg"},
    "Мона":     {"region": "mondstadt", "image": "https://avatars.mds.yandex.net/i?id=e2edb70acce72929e4d92d4b5b9b0462_l-9181118-images-thumbs&n=13"},
    "Ноэлль":   {"region": "mondstadt", "image": "https://i.pinimg.com/originals/fe/de/c6/fedec64b9316f0b372612856733bc1cf.jpg"},
    "Розария":  {"region": "mondstadt", "image": "https://i.pinimg.com/originals/ff/b7/f0/ffb7f04cb79fec178d2dc28733cf0409.jpg?nii=t"},
    "Рэйзор":   {"region": "mondstadt", "image": "https://i.pinimg.com/originals/fc/03/c7/fc03c705f3403106b706824d7d56485b.jpg?nii=t"},
    "Сахароза": {"region": "mondstadt", "image": "https://cdn.kanobu.ru/r/17a951640058e44b3248759d71577452/1040x-/cdn.kanobu.ru/editor/images/22/86b724b5-42db-4c1e-b293-008230ea1cda.jpeg"},
    "Фишль":    {"region": "mondstadt", "image": "https://i.pinimg.com/originals/74/73/61/7473610cd0846c75b6c722548cd78c3f.jpg"},
    "Эмбер":    {"region": "mondstadt", "image": "https://avatars.mds.yandex.net/i?id=55ad915132f6fc1b7445b04a30b8c098_l-4567989-images-thumbs&n=13"},
    "Эола":     {"region": "mondstadt", "image": "https://avatars.mds.yandex.net/i?id=60f1bc74e3b8dd513f6b0d2f4f185d0c_l-12423213-images-thumbs&n=13"},
    "Далия":    {"region": "mondstadt", "image": "https://static0.gamerantimages.com/wordpress/wp-content/uploads/2025/05/genshin-7.jpg"},
    "Лоэн":     {"region": "mondstadt", "image": "https://i.pinimg.com/originals/fd/85/8a/fd858a6ff60c4a0f2eb4263edd52f973.jpg"},
    "Дурин":    {"region": "mondstadt", "image": "https://avatars.mds.yandex.net/i?id=25d7478de147fda2abd0c7d06e60dfd7_l-7025550-images-thumbs&n=13"},
    "Николь":   {"region": "mondstadt", "image": "https://avatars.mds.yandex.net/i?id=5f52ba1038a6f52ca3a058805fc4367a_l-12734301-images-thumbs&n=13"},
    "Варка":    {"region": "mondstadt", "image": "https://i.pinimg.com/originals/11/3a/95/113a957547cebfeff62519f24d0f31e4.jpg"},
    "Алиса":    {"region": "mondstadt", "image": "https://avatars.mds.yandex.net/i?id=4022d47cdc63fa0ca84dc069d0f77494_l-4491259-images-thumbs&n=13"},
    "Прюн":     {"region": "mondstadt", "image": "https://avatars.mds.yandex.net/i?id=eca890b12766f71bbe9c32b3ce3ba041_l-4612938-images-thumbs&n=13"},

    # ===== Ли Юэ =====
    "Бай Чжу":   {"region": "liyue", "image": "https://i.pinimg.com/originals/01/91/74/019174b78936986483855e23ffe6528f.jpg?nii=t"},
    "Бэй Доу":   {"region": "liyue", "image": "https://cdn.vexagame.com/blog/blog/wp-content/uploads/2021/03/Build-Beidou-Genshin-Impact-4.jpeg"},
    "Гань Юй":   {"region": "liyue", "image": "https://i.pinimg.com/originals/8a/66/ad/8a66adf88e458f929dadd5adf2dee577.webp?nii=t"},
    "Е Лань":    {"region": "liyue", "image": "https://i.pinimg.com/originals/fb/55/95/fb5595c40d3c20c0662991877d61fb16.jpg"},
    "Кэ Цин":    {"region": "liyue", "image": "https://i.pinimg.com/originals/68/9f/20/689f202a336c390f5337d4685ad8ad7b.jpg?nii=t"},
    "Нин Гуан":  {"region": "liyue", "image": "https://i.pinimg.com/originals/12/3f/d3/123fd306a7e2428c1c2bfe26906ee958.jpg"},
    "Син Цю":    {"region": "liyue", "image": "https://avatars.mds.yandex.net/i?id=282c9d1fded92b3477ca47d1c7efdace_l-4230319-images-thumbs&n=13"},
    "Синь Янь":  {"region": "liyue", "image": "https://avatars.mds.yandex.net/i?id=acb469b8e318604adfb6f92c9534debe_l-5505644-images-thumbs&n=13"},
    "Сян Лин":   {"region": "liyue", "image": "https://cdn.kanobu.ru/r/eac100f06f723190a4ecce695c107902/1040x-/cdn.kanobu.ru/editor/images/28/0d738e6e-2500-4263-8c0b-45b7de72d6a2.jpg"},
    "Сяо":       {"region": "liyue", "image": "https://avatars.mds.yandex.net/i?id=b3ed1c54ec0c9c8cfc7e77e11dd37f90_l-5163701-images-thumbs&n=13"},
    "Ху Тао":    {"region": "liyue", "image": "https://i.pinimg.com/originals/71/a4/7d/71a47d24b7a8c48330da147a79711f6c.jpg"},
    "Цици":      {"region": "liyue", "image": "https://i.pinimg.com/originals/9f/31/98/9f31988310b2f8fe856fa7ae09a9e6a0.jpg?nii=t"},
    "Чжун Ли":   {"region": "liyue", "image": "https://avatars.mds.yandex.net/i?id=bfa5b83f843bb9ced211b76a3ac81ca6_l-5221370-images-thumbs&n=13"},
    "Чунь Юнь":  {"region": "liyue", "image": "https://i.pinimg.com/originals/17/08/ab/1708abeb8808c73d0ba42b3506fa865f.png"},
    "Шэнь Хэ":   {"region": "liyue", "image": "https://i.pinimg.com/originals/7d/90/e8/7d90e88a32f0f09270e98ba2b75d618e.jpg?nii=t"},
    "Юнь Цзинь": {"region": "liyue", "image": "https://i.pinimg.com/originals/3b/11/c5/3b11c5a72f2cb89cd8bdf2117e147405.jpg"},
    "Янь Фэй":   {"region": "liyue", "image": "https://storage.respawn.media/zaaur7A9gaEvcOoxejsog.webp"},
    "Яо Яо":     {"region": "liyue", "image": "https://avatars.mds.yandex.net/i?id=d1f506c59aa52e4ee3f1b5fea6a5b011_l-8071172-images-thumbs&n=13"},
    "Га Мин":    {"region": "liyue", "image": "https://avatars.mds.yandex.net/i?id=57bf2c02e9b58310b44c0565ac448fa0_l-10241101-images-thumbs&n=13"},
    "Лань Янь":  {"region": "liyue", "image": "https://avatars.mds.yandex.net/i?id=179ada77538095709cf08c3f496e6dd2_l-10756139-images-thumbs&n=13"},
    "Сянь Юнь":  {"region": "liyue", "image": "https://i.pinimg.com/originals/ac/1c/01/ac1c0147de6b85c397ed398b7ec4b93b.jpg"},

    # ===== Инадзума =====
    "Аяка Камисато": {"region": "inazuma", "image": "https://upload-os-bbs.hoyolab.com/upload/2023/03/20/160526120/0103999477aa7373d945ac9bd9c96d55_8877000270073418861.jpg"},
    "Аято Камисато": {"region": "inazuma", "image": "https://i.pinimg.com/originals/51/be/d7/51bed722a67a792d9296c22169ac76e8.jpg"},
    "Горо":          {"region": "inazuma", "image": "https://i.pinimg.com/originals/e5/cf/ba/e5cfbaa53745f382a65f6f838f24b5f1.jpg"},
    "Ёимия":         {"region": "inazuma", "image": "https://i.playground.ru/p/OvHn5alcBrV34k6h1PnHfw.png"},
    "Итто":          {"region": "inazuma", "image": "https://avatars.mds.yandex.net/i?id=370be7a8cabac5ce8b5ad992ceb48115_l-5224388-images-thumbs&n=13"},
    "Кадзуха":       {"region": "inazuma", "image": "https://avatars.mds.yandex.net/i?id=f762216370361c7d28fc5bdcf3733af2_l-5887538-images-thumbs&n=13"},
    "Кирара":        {"region": "inazuma", "image": "https://konachan.net/sample/6b88a8d4cde9ca9b5ad8ff8e255a17f7/Konachan.com%20-%20376374%20sample.jpg"},
    "Кокоми":        {"region": "inazuma", "image": "https://vkplay.ru/pre_0x736_resize/hotbox/content_files/article/2021/09/14/739f893c60374960bbf310465e6139d0.jpg?quality=85"},
    "Райдэн Эи":     {"region": "inazuma", "image": "https://i.pinimg.com/originals/d7/e5/f8/d7e5f829a75b32c40cf7922906eaaa64.jpg?nii=t"},
    "Сара":          {"region": "inazuma", "image": "https://cdnb.artstation.com/p/assets/images/images/049/458/895/large/bolidraws-asdf.jpg?1652544361"},
    "Саю":           {"region": "inazuma", "image": "https://avatars.mds.yandex.net/i?id=2126621f3878a99ece2525fed104befb_l-5220825-images-thumbs&n=13"},
    "Синобу":        {"region": "inazuma", "image": "https://cdnb.artstation.com/p/assets/images/images/068/372/271/medium/yu4-kuki-burst.jpg?1697643244"},
    "Тома":          {"region": "inazuma", "image": "https://i.pinimg.com/originals/c6/fb/ba/c6fbbaf61df605c87400f305be7530a0.jpg?nii=t"},
    "Хэйдзо":        {"region": "inazuma", "image": "https://avatars.mds.yandex.net/i?id=20ac9614bdfeb2dfc2f4d2d4f948a602_l-10289922-images-thumbs&n=13"},
    "Яэ Мико":       {"region": "inazuma", "image": "https://avatars.mds.yandex.net/i?id=9f721f87a4db4831e8c07e52793964bb_l-4575864-images-thumbs&n=13"},
    "Тиори":         {"region": "inazuma", "image": "https://avatars.mds.yandex.net/i?id=34b0fb2c53e13ea4a824314f6dc46ce2_l-4475612-images-thumbs&n=13"},
    "Мидзуки":       {"region": "inazuma", "image": "https://avatars.mds.yandex.net/i?id=00afb6715c5973242340a915c45d9889_l-4349375-images-thumbs&n=13"},

    # ===== Сумеру =====
    "Аль-Хайтам": {"region": "sumeru", "image": "https://i.pinimg.com/originals/dc/a1/ae/dca1ae03711df459250e9bfd78d32779.jpg?nii=t"},
    "Дори":       {"region": "sumeru", "image": "https://avatars.mds.yandex.net/i?id=f72e2669ef9233b54b745c67cb8a0348_l-4724279-images-thumbs&n=13"},
    "Дэхья":      {"region": "sumeru", "image": "https://avatars.mds.yandex.net/i?id=134c665af09892405613ade6b7ed33e2_l-5225319-images-thumbs&n=13"},
    "Кавех":      {"region": "sumeru", "image": "https://i.pinimg.com/originals/e8/69/c3/e869c3da2575d5ea5723b922ef833aeb.jpg"},
    "Кандакия":   {"region": "sumeru", "image": "https://avatars.mds.yandex.net/i?id=e4caafc5878ddc5eb42aa50c97bd80aca9596d76-5233020-images-thumbs&n=13"},
    "Коллеи":     {"region": "sumeru", "image": "https://avatars.mds.yandex.net/i?id=8bb3f2c962b1776e8dcade49b13aea2c_l-4590012-images-thumbs&n=13"},
    "Лайла":      {"region": "sumeru", "image": "https://i.pinimg.com/originals/19/8a/c2/198ac20bc26dfbbe173b1fbc1ae94114.jpg"},
    "Нахида":     {"region": "sumeru", "image": "https://i.pinimg.com/originals/b5/00/94/b50094b39583e0d067ac43915a01c0f8.jpg"},
    "Нилу":       {"region": "sumeru", "image": "https://i.pinimg.com/originals/b8/21/34/b82134a30b0504dc54009cab806112af.jpg?nii=t"},
    "Сайно":      {"region": "sumeru", "image": "https://i.pinimg.com/originals/90/26/ca/9026cae334512b963de099d3349cca62.jpg?nii=t"},
    "Сетос":      {"region": "sumeru", "image": "https://avatars.mds.yandex.net/i?id=5fb0a39f9a9c073578d7ce6001bb9852_l-9866669-images-thumbs&n=13"},
    "Странник":   {"region": "sumeru", "image": "https://i.pinimg.com/originals/ec/56/7a/ec567a5962edfd18f6849985c7a86bbe.jpg?nii=t"},
    "Тигнари":    {"region": "sumeru", "image": "https://avatars.mds.yandex.net/i?id=93a67629e37bd8e6c7dbf75be208bd56_l-9838181-images-thumbs&n=13"},
    "Фарузан":    {"region": "sumeru", "image": "https://i.pinimg.com/736x/01/52/96/01529633bb14670ce30415c976f4710e.jpg"},

    # ===== Фонтейн =====
    "Клоринда": {"region": "fontaine", "image": "https://i.pinimg.com/originals/60/a0/fe/60a0fe27a5d0094502a6988b5d250894.jpg?nii=t"},
    "Лини":     {"region": "fontaine", "image": "https://i.pinimg.com/originals/61/95/3e/61953e0d0a7eb03a71e30dc26bb3c90c.jpg"},
    "Линнет":   {"region": "fontaine", "image": "https://i.pinimg.com/originals/77/b8/77/77b877fdaeb210a143c2b180835f4de7.jpg"},
    "Навия":    {"region": "fontaine", "image": "https://media.ixbt.games/fit-in/3000x/https://ixbt.online/publications/2023/07/03/EnWBazzNVoaa19D14c8sL4SUFp1GI5OI9SlvObQu.png"},
    "Нёвиллет": {"region": "fontaine", "image": "https://i.pinimg.com/originals/eb/9f/96/eb9f96d6b9ade9759766f4e66f6e5f3a.jpg"},
    "Ризли":    {"region": "fontaine", "image": "https://avatars.mds.yandex.net/i?id=f60eb8dadc8cfe84b19629ed2fde2a06_l-4599771-images-thumbs&n=13"},
    "Сиджвин":  {"region": "fontaine", "image": "https://avatars.mds.yandex.net/i?id=61de0400320efb336ef23c2cbc6a3998_l-11005657-images-thumbs&n=13"},
    "Фремине":  {"region": "fontaine", "image": "https://upload-os-bbs.hoyolab.com/upload/2025/06/04/451791304/b252ea1f39dea94f6bae920280fc9841_5950687807543973865.jpeg"},
    "Фурина":   {"region": "fontaine", "image": "https://avatars.mds.yandex.net/i?id=1519f5f7883a9638c4d7ff922a7d0ae4_l-5378866-images-thumbs&n=13"},
    "Шарлотта": {"region": "fontaine", "image": "https://i.pinimg.com/736x/6a/7f/1c/6a7f1cc3a7aa01989171cdfc8131cfd6.jpg"},
    "Шеврёз":   {"region": "fontaine", "image": "https://i.pinimg.com/originals/f4/8b/d1/f48bd1b042147a5e219d4df68df5b0d9.jpg"},
    "Эмилия":   {"region": "fontaine", "image": "https://images.cybersport.ru/images/og-jpg/plain/37/37e27cdb-02a2-4635-a8d5-9326df7be828.webp"},
    "Эскофье":  {"region": "fontaine", "image": "https://i.pinimg.com/originals/b5/b8/d0/b5b8d00e23e842e0c4b844d6f9bb960d.jpg"},

    # ===== Натлан =====
    "Вареса":  {"region": "natlan", "image": "https://i.pinimg.com/originals/74/3d/e8/743de8fe94c02a933fe6a3ccf31a5135.jpg"},
    "Иансан":  {"region": "natlan", "image": "https://avatars.mds.yandex.net/i?id=214422e223d358096ef1d3ab63f159fb_l-11501519-images-thumbs&n=13"},
    "Ифа":     {"region": "natlan", "image": "https://avatars.mds.yandex.net/i?id=9af277f73f31b98cbba596f918c170fa_l-12808915-images-thumbs&n=13"},
    "Качина":  {"region": "natlan", "image": "https://avatars.mds.yandex.net/i?id=11392916db5cb0378eefdaccc7177035_l-5235635-images-thumbs&n=13"},
    "Кинич":   {"region": "natlan", "image": "https://i.pinimg.com/originals/12/34/2d/12342daca5387d8dc77609925e0209a8.jpg?nii=t"},
    "Мавуика": {"region": "natlan", "image": "https://i.pinimg.com/originals/4f/c4/8c/4fc48cbef5633a85992fb11e7d29746a.jpg"},
    "Муалани": {"region": "natlan", "image": "https://i.pinimg.com/originals/26/fd/f4/26fdf4c3d536b43d2e8514326faae7ca.jpg?nii=t"},
    "Оророн":  {"region": "natlan", "image": "https://i.pinimg.com/originals/81/84/65/818465a1ed9cbcfa7f657fe5dec31fe8.webp"},
    "Ситлали": {"region": "natlan", "image": "https://avatars.mds.yandex.net/i?id=4a999093a7d76e382c3ab8ee91c47da9_l-5325461-images-thumbs&n=13"},
    "Часка":   {"region": "natlan", "image": "https://i.pinimg.com/736x/c2/57/9f/c2579f907a251507919fd872944cf393.jpg"},
    "Шилонен": {"region": "natlan", "image": "https://wotpack.ru/wp-content/uploads/2024/07/Shilonen-v-Genshin-Impact.jpg"},

    # ===== Нод-Край =====
    "Айно":      {"region": "nodkrai", "image": "https://rbkgames.com/wp-content/uploads/2025/07/gamestatic-e4e1295a4068b5fc63244a989dbfdf0f.jpg"},
    "Иллуга":    {"region": "nodkrai", "image": "https://avatars.mds.yandex.net/i?id=3becda62fc503b9393907524fc9264b5_l-5504462-images-thumbs&n=13"},
    "Коломбина": {"region": "nodkrai", "image": "https://wotpack.ru/wp-content/uploads/2023/03/word-image-220170-14.jpg"},
    "Лаума":     {"region": "nodkrai", "image": "https://avatars.mds.yandex.net/i?id=23cc3b35d7ef56fdfc5a895f99a18cc3_l-12472935-images-thumbs&n=13"},
    "Нефер":     {"region": "nodkrai", "image": "https://avatars.mds.yandex.net/i?id=faef8e3b716b3a82403a26bfcde322b5_l-4417533-images-thumbs&n=13"},
    "Флинс":     {"region": "nodkrai", "image": "https://i.pinimg.com/originals/7b/a5/2e/7ba52ea63b5d379feeabc1052e9400bc.jpg"},
    "Ягода":     {"region": "nodkrai", "image": "https://avatars.mds.yandex.net/i?id=f523a872f766a9db3c38e0001f98f48c_l-9151250-images-thumbs&n=13"},
    "Инеффа":    {"region": "nodkrai", "image": "https://avatars.mds.yandex.net/i?id=8f3cf1c7f299c28642645cb4a315e92b_l-3553471-images-thumbs&n=13"},
    "Линнея":    {"region": "nodkrai", "image": "https://avatars.mds.yandex.net/i?id=5b7b66fa522266b23917a5675265bd2a_l-3793502-images-thumbs&n=13"},

    # ===== Снежная =====
    "Алёша":       {"region": "snezhnaya", "image": "https://i.pinimg.com/originals/e3/15/41/e315411f884980ecc476d55b6e6b2032.jpg?nii=t"},
    "Арлекино":    {"region": "snezhnaya", "image": "https://avatars.mds.yandex.net/i?id=68adc0eb0cf1798a5fdec547049d44dd_l-8797427-images-thumbs&n=13"},
    "Одетта":      {"region": "snezhnaya", "image": "https://avatars.mds.yandex.net/i?id=5a6b4533ce63b79370c549bd4776df4f_l-5235953-images-thumbs&n=13"},
    "Сандроне":    {"region": "snezhnaya", "image": "https://i.pinimg.com/originals/bd/4d/60/bd4d60dba93ba531069e1367b25b1471.png"},
    "Тарталья":    {"region": "snezhnaya", "image": "https://avatars.mds.yandex.net/i?id=e64a8909f8dd516b29adb5447a4ef8c1_l-5024131-images-thumbs&n=13"},
    "Пульчинелла": {"region": "snezhnaya", "image": "https://avatars.mds.yandex.net/i?id=2fa8e8b73619ffd535109db180ae5925_l-5150842-images-thumbs&n=13"},
    "Панталоне":   {"region": "snezhnaya", "image": "https://avatars.mds.yandex.net/i?id=de3fef51dab808f74c3357384291d0bbc7e02d01-8129946-images-thumbs&n=13"},
    "Дотторе":     {"region": "snezhnaya", "image": "https://avatars.mds.yandex.net/i?id=450a11395d951cde3b88ed96dc018ef9_l-4356414-images-thumbs&n=13"},
    "Капитано":    {"region": "snezhnaya", "image": "https://avatars.mds.yandex.net/i?id=2cc985d18d5c398a75aabd1642f81486_l-9269009-images-thumbs&n=13"},
    "Пьеро":       {"region": "snezhnaya", "image": "https://avatars.mds.yandex.net/i?id=7403e1fb95bd7958060de118150e3349_l-4576013-images-thumbs&n=13"},
    "Синьора":     {"region": "snezhnaya", "image": "https://avatars.mds.yandex.net/i?id=27a09bed8a8ed2f57cb63d8e081985eb_l-5284089-images-thumbs&n=13"},
    "Царица":      {"region": "snezhnaya", "image": "https://avatars.mds.yandex.net/i?id=db2a6708ea7303ce3aae534e6dd84e16_l-10303547-images-thumbs&n=13"},
    "Весна":       {"region": "snezhnaya", "image": "https://avatars.mds.yandex.net/i?id=ae9583b77b4920b8a5a52b3c3c609025_l-5714596-images-thumbs&n=13"},
    "Водяница":    {"region": "snezhnaya", "image": "https://avatars.mds.yandex.net/i?id=3a037def437c3c83babacca9d97679c1_l-8221351-images-thumbs&n=13"},
    "Цзы Бай":     {"region": "snezhnaya", "image": "https://avatars.mds.yandex.net/i?id=d8700db8b5995eff33d318d13b68b59d_l-5485739-images-thumbs&n=13"},
    "Валерий":     {"region": "snezhnaya", "image": "https://wotpack.ru/wp-content/uploads/2026/06/litso-valeriya-vblizi-genshin-impact-1536x864.jpg"},
    "Митя":        {"region": "snezhnaya", "image": "https://avatars.mds.yandex.net/i?id=0a742c3c56117b4098fb93a80d441418_l-5287068-images-thumbs&n=13"},

    # ===== Другие =====
    "Дайнслейф": {"region": "other", "image": "https://avatars.mds.yandex.net/i?id=7c1d18512691e709a240628ca6e41424_l-9862264-images-thumbs&n=13"},
    "Итэр":      {"region": "other", "image": "https://i.pinimg.com/originals/36/18/bf/3618bfd1c265bd0a7ddab009288939f2.jpg"},
    "Люмин":     {"region": "other", "image": "https://i.pinimg.com/originals/5f/a0/63/5fa063f5218f5a27a3479c97da917561.jpg"},
    "Паймон":    {"region": "other", "image": "https://genshin.jmp.blue/characters/paimon/portrait"},
    "Скирк":     {"region": "other", "image": "https://i.pinimg.com/originals/8d/d9/b2/8dd9b23eb424f80efde68d940dcb7e77.jpg"},
    "Элой":      {"region": "other", "image": "https://avatars.mds.yandex.net/i?id=8564e7b7366a0072463effa4c571d486_l-4146308-images-thumbs&n=13"},
}


def get_characters_by_region(region_key: str):
    return [name for name, data in CHARACTERS.items() if data["region"] == region_key]


def get_character_image(character_name: str) -> str:
    data = CHARACTERS.get(character_name)
    if data:
        return data["image"]
    return "https://genshin.jmp.blue/characters/aether/portrait"


def get_character_region(character_name: str) -> str:
    data = CHARACTERS.get(character_name)
    if data:
        return data["region"]
    return "other"

import unicodedata

EN_TO_RU = {
    # Мондштадт
    "albedo": "Альбедо", "barbara": "Барбара", "bennett": "Беннет",
    "venti": "Венти", "jean": "Джинн", "diluc": "Дилюк", "diona": "Диона",
    "klee": "Кли", "kaeya": "Кэйа", "lisa": "Лиза", "mika": "Мика",
    "mona": "Мона", "noelle": "Ноэлль", "rosaria": "Розария",
    "razor": "Рэйзор", "sucrose": "Сахароза", "fischl": "Фишль",
    "amber": "Эмбер", "eula": "Эола", "dahlia": "Далия",
    "lohen": "Лоэн", "durin": "Дурин", "nicole": "Николь",
    "barka": "Варка", "alice": "Алиса", "prun": "Прюн",
    # Ли Юэ
    "baizhu": "Бай Чжу", "beidou": "Бэй Доу", "ganyu": "Гань Юй",
    "yelan": "Е Лань", "keqing": "Кэ Цин", "ningguang": "Нин Гуан",
    "xingqiu": "Син Цю", "xinyan": "Синь Янь", "xiangling": "Сян Лин",
    "xiao": "Сяо", "hutao": "Ху Тао", "hu-tao": "Ху Тао", "qiqi": "Цици",
    "zhongli": "Чжун Ли", "zhong-li": "Чжун Ли", "chongyun": "Чунь Юнь",
    "shenhe": "Шэнь Хэ", "yunjin": "Юнь Цзинь", "yanfei": "Янь Фэй",
    "yaoyao": "Яо Яо", "gaming": "Га Мин", "lanyan": "Лань Янь", "xianyun": "Сянь Юнь",
    # Инадзума
    "ayaka": "Аяка Камисато", "kamisatoayaka": "Аяка Камисато",
    "ayato": "Аято Камисато", "kamisatoayato": "Аято Камисато",
    "gorou": "Горо", "yoimiya": "Ёимия", "itto": "Итто", "aratakiitto": "Итто",
    "kazuha": "Кадзуха", "kaedeharakazuha": "Кадзуха",
    "kirara": "Кирара", "kokomi": "Кокоми", "sangonomiyakokomi": "Кокоми",
    "raiden": "Райдэн Эи", "raidenshogun": "Райдэн Эи",
    "sara": "Сара", "kujousara": "Сара", "sayu": "Саю",
    "shinobu": "Синобу", "kukishinobu": "Синобу", "thoma": "Тома",
    "heizou": "Хэйдзо", "shikanoinheizou": "Хэйдзо",
    "yae": "Яэ Мико", "yaemiko": "Яэ Мико", "miko": "Яэ Мико",
    "chiori": "Тиори", "mizuki": "Мидзуки",
    # Сумеру
    "alhaitham": "Аль-Хайтам", "dori": "Дори", "dehya": "Дэхья",
    "kaveh": "Кавех", "candace": "Кандакия", "collei": "Коллеи",
    "layla": "Лайла", "nahida": "Нахида", "nilou": "Нилу",
    "cyno": "Сайно", "sethos": "Сетос", "wanderer": "Странник",
    "scaramouche": "Странник", "tighnari": "Тигнари", "faruzan": "Фарузан",
    # Фонтейн
    "clorinde": "Клоринда", "lyney": "Лини", "lynette": "Линнет",
    "navia": "Навия", "neuvillette": "Нёвиллет", "wriothesley": "Ризли",
    "sigewinne": "Сиджвин", "freminet": "Фремине", "furina": "Фурина",
    "charlotte": "Шарлотта", "chevreuse": "Шеврёз", "emilie": "Эмилия",
    "escoffier": "Эскофье",
    # Натлан
    "varesa": "Вареса", "iansan": "Иансан", "ifa": "Ифа",
    "kachina": "Качина", "kinich": "Кинич", "mavuika": "Мавуика",
    "mualani": "Муалани", "ororon": "Оророн", "citlali": "Ситлали",
    "chasca": "Часка", "xilonen": "Шилонен",
    # Нод-Край
    "aino": "Айно", "illuga": "Иллуга", "columbina": "Коломбина",
    "lauma": "Лаума", "nefer": "Нефер", "flins": "Флинс",
    "yagoda": "Ягода", "ineffa": "Инеффа", "linnea": "Линнея",
    # Снежная
    "alyosha": "Алёша", "arlecchino": "Арлекино", "odette": "Одетта",
    "sandrone": "Сандроне", "tartaglia": "Тарталья", "childe": "Тарталья",
    "pulcinella": "Пульчинелла", "pantalone": "Панталоне", "dottore": "Дотторе",
    "capitano": "Капитано", "pierro": "Пьеро", "signora": "Синьора",
    "tsaritsa": "Царица", "vesna": "Весна", "vodyanitsa": "Водяница",
    "zybai": "Цзы Бай", "valeriy": "Валерий", "mitya": "Митя",
    # Другие
    "dainsleif": "Дайнслейф", "aether": "Итэр", "lumine": "Люмин",
    "paimon": "Паймон", "skirk": "Скирк", "aloy": "Элой"
}

def normalize_character_name(text: str) -> str:
    if not text:
        return ""
    cleaned = unicodedata.normalize("NFKC", text).strip()
    search_key = cleaned.lower().replace(" ", "").replace("-", "").replace("_", "")
    if search_key in EN_TO_RU:
        return EN_TO_RU[search_key]
    return cleaned.title()

# ==================== АВТОПЕРЕВОД И ОЧИСТКА ШРИФТОВ ====================
import unicodedata

# Полный словарь английских имен в русские (включая альтернативные написания)
EN_TO_RU = {
    # Мондштадт
    "albedo": "Альбедо", "barbara": "Барбара", "bennett": "Беннет",
    "venti": "Венти", "jean": "Джинн", "diluc": "Дилюк", "diona": "Диона",
    "klee": "Кли", "kaeya": "Кэйа", "lisa": "Лиза", "mika": "Мика",
    "mona": "Мона", "noelle": "Ноэлль", "rosaria": "Розария",
    "razor": "Рэйзор", "sucrose": "Сахароза", "fischl": "Фишль",
    "amber": "Эмбер", "eula": "Эола", "dahlia": "Далия",
    "lohen": "Лоэн", "durin": "Дурин", "nicole": "Николь",
    "barka": "Варка", "alice": "Алиса", "prun": "Прюн",

    # Ли Юэ
    "baizhu": "Бай Чжу", "beidou": "Бэй Доу", "ganyu": "Гань Юй",
    "yelan": "Е Лань", "keqing": "Кэ Цин", "ningguang": "Нин Гуан",
    "xingqiu": "Син Цю", "xinyan": "Синь Янь", "xiangling": "Сян Лин",
    "xiao": "Сяо", "hutao": "Ху Тао", "hu-tao": "Ху Тао", "qiqi": "Цици",
    "zhongli": "Чжун Ли", "zhong-li": "Чжун Ли", "chongyun": "Чунь Юнь",
    "shenhe": "Шэнь Хэ", "yunjin": "Юнь Цзинь", "yanfei": "Янь Фэй",
    "yaoyao": "Яо Яо", "gaming": "Га Мин", "lanyan": "Лань Янь", "xianyun": "Сянь Юнь",

    # Инадзума
    "ayaka": "Аяка Камисато", "kamisatoayaka": "Аяка Камисато",
    "ayato": "Аято Камисато", "kamisatoayato": "Аято Камисато",
    "gorou": "Горо", "yoimiya": "Ёимия", "itto": "Итто", "aratakiitto": "Итто",
    "kazuha": "Кадзуха", "kaedeharakazuha": "Кадзуха",
    "kirara": "Кирара", "kokomi": "Кокоми", "sangonomiyakokomi": "Кокоми",
    "raiden": "Райдэн Эи", "raidenshogun": "Райдэн Эи",
    "sara": "Сара", "kujousara": "Сара", "sayu": "Саю",
    "shinobu": "Синобу", "kukishinobu": "Синобу", "thoma": "Тома",
    "heizou": "Хэйдзо", "shikanoinheizou": "Хэйдзо",
    "yae": "Яэ Мико", "yaemiko": "Яэ Мико", "miko": "Яэ Мико",
    "chiori": "Тиори", "mizuki": "Мидзуки",

    # Сумеру
    "alhaitham": "Аль-Хайтам", "dori": "Дори", "dehya": "Дэхья",
    "kaveh": "Кавех", "candace": "Кандакия", "collei": "Коллеи",
    "layla": "Лайла", "nahida": "Нахида", "nilou": "Нилу",
    "cyno": "Сайно", "sethos": "Сетос", "wanderer": "Странник",
    "scaramouche": "Странник", "tighnari": "Тигнари", "faruzan": "Фарузан",

    # Фонтейн
    "clorinde": "Клоринда", "lyney": "Лини", "lynette": "Линнет",
    "navia": "Навия", "neuvillette": "Нёвиллет", "wriothesley": "Ризли",
    "sigewinne": "Сиджвин", "freminet": "Фремине", "furina": "Фурина",
    "charlotte": "Шарлотта", "chevreuse": "Шеврёз", "emilie": "Эмилия",
    "escoffier": "Эскофье",

    # Натлан
    "varesa": "Вареса", "iansan": "Иансан", "ifa": "Ифа",
    "kachina": "Качина", "kinich": "Кинич", "mavuika": "Мавуика",
    "mualani": "Муалани", "ororon": "Оророн", "citlali": "Ситлали",
    "chasca": "Часка", "xilonen": "Шилонен",

    # Нод-Край
    "aino": "Айно", "illuga": "Иллуга", "columbina": "Коломбина",
    "lauma": "Лаума", "nefer": "Нефер", "flins": "Флинс",
    "yagoda": "Ягода", "ineffa": "Инеффа", "linnea": "Линнея",

    # Снежная
    "alyosha": "Алёша", "arlecchino": "Арлекино", "odette": "Одетта",
    "sandrone": "Сандроне", "tartaglia": "Тарталья", "childe": "Тарталья",
    "pulcinella": "Пульчинелла", "pantalone": "Панталоне", "dottore": "Дотторе",
    "capitano": "Капитано", "pierro": "Пьеро", "signora": "Синьора",
    "tsaritsa": "Царица", "vesna": "Весна", "vodyanitsa": "Водяница",
    "zybai": "Цзы Бай", "valeriy": "Валерий", "mitya": "Митя",

    # Другие
    "dainsleif": "Дайнслейф", "aether": "Итэр", "lumine": "Люмин",
    "paimon": "Паймон", "skirk": "Скирк", "aloy": "Элой"
}

def normalize_character_name(text: str) -> str:
    """
    Очищает текст от кастомных шрифтов и переводит англ. имена на русский.
    Например: '𝓗𝓾 𝓣𝓪𝓸' -> 'Ху Тао', 'kazuha' -> 'Кадзуха'.
    """
    if not text:
        return ""
    
    # NFKC нормализует кастомные шрифты (превращает 𝓗𝓾 𝓣𝓪𝓸 в Hu Tao)
    cleaned = unicodedata.normalize("NFKC", text).strip()
    
    # Убираем лишние пробелы и переводим в нижний регистр для поиска
    search_key = cleaned.lower().replace(" ", "").replace("-", "").replace("_", "")
    
    if search_key in EN_TO_RU:
        return EN_TO_RU[search_key]
        
    # Если это русское имя, просто возвращаем с большой буквы
    return cleaned.title()