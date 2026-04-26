from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.database import get_session_factory
from backend.app.core.security import hash_password
from backend.app.models.admin import AdminUser
from backend.app.models.membership import MemberLevel
from backend.app.models.product import (
    Category,
    Inventory,
    Product,
    ProductMedia,
    ProductSku,
    ProductTag,
)

CATEGORY_SEEDS = [
    {"name": "汉服", "slug": "hanfu", "description": "传统汉服服饰"},
    {"name": "文创", "slug": "wenchuang", "description": "传统文化衍生设计"},
    {"name": "非遗", "slug": "feiyi", "description": "非遗手工艺精品"},
    {"name": "饰品", "slug": "accessory", "description": "古风配饰与点缀"},
    {"name": "礼盒", "slug": "gift-box", "description": "节令与送礼礼盒"},
]

DEFAULT_ADMIN_USER = {
    "email": "admin@shiyige-demo.com",
    "username": "admin",
    "password": "admin123456",
    "role": "super_admin",
}

MEMBER_LEVEL_SEEDS = [
    {
        "code": "bronze",
        "name": "青铜会员",
        "level_order": 1,
        "min_points": 0,
        "discount_rate": Decimal("0.98"),
        "points_rate": Decimal("1.00"),
        "description": "基础会员等级，享受基础折扣与积分倍率。",
        "is_default": True,
    },
    {
        "code": "silver",
        "name": "白银会员",
        "level_order": 2,
        "min_points": 1000,
        "discount_rate": Decimal("0.95"),
        "points_rate": Decimal("1.20"),
        "description": "适合稳定复购用户的进阶会员等级。",
        "is_default": False,
    },
    {
        "code": "gold",
        "name": "黄金会员",
        "level_order": 3,
        "min_points": 5000,
        "discount_rate": Decimal("0.92"),
        "points_rate": Decimal("1.50"),
        "description": "适合高频消费用户的高等级会员。",
        "is_default": False,
    },
    {
        "code": "platinum",
        "name": "铂金会员",
        "level_order": 4,
        "min_points": 20000,
        "discount_rate": Decimal("0.88"),
        "points_rate": Decimal("2.00"),
        "description": "当前最高等级会员，享受最高折扣与积分倍率。",
        "is_default": False,
    },
]

PRODUCT_SEEDS = [
    {
        "category_slug": "hanfu",
        "name": "明制襦裙",
        "subtitle": "海棠红刺绣款",
        "cover_url": "images/汉服/明制襦裙1.jpg",
        "description": "明制襦裙，适合春日出游与传统活动。",
        "culture_summary": "襦裙是汉服的经典形制之一，体现礼制与审美并重的着装传统。",
        "dynasty_style": "明制",
        "craft_type": "刺绣",
        "festival_tag": "春游",
        "scene_tag": "出游",
        "tags": ["汉服", "明制", "春日"],
        "media_urls": ["images/汉服/明制襦裙1.jpg", "images/汉服/明制襦裙2.jpg"],
        "price": Decimal("899.00"),
        "member_price": Decimal("799.00"),
        "stock": 12,
    },
    {
        "category_slug": "hanfu",
        "name": "汉元素对襟",
        "subtitle": "轻日常改良款",
        "cover_url": "images/汉服/汉元素对襟1.jpg",
        "description": "适合日常通勤的汉元素对襟上衣。",
        "culture_summary": "改良汉服让传统服饰以更低门槛进入当代生活场景。",
        "dynasty_style": "宋制",
        "craft_type": "织造",
        "festival_tag": "日常",
        "scene_tag": "通勤",
        "tags": ["汉元素", "对襟", "通勤"],
        "media_urls": ["images/汉服/汉元素对襟1.jpg", "images/汉服/汉元素对襟2.jpg"],
        "price": Decimal("459.00"),
        "member_price": Decimal("399.00"),
        "stock": 18,
    },
    {
        "category_slug": "hanfu",
        "name": "唐制交领袍",
        "subtitle": "宽袍大袖礼服款",
        "cover_url": "images/汉服/唐制交领袍1.jpg",
        "description": "庄重大气的唐制交领袍，适合活动拍摄。",
        "culture_summary": "唐制服饰展现盛唐时期开放与恢弘的审美气象。",
        "dynasty_style": "唐制",
        "craft_type": "提花",
        "festival_tag": "节庆",
        "scene_tag": "活动",
        "tags": ["唐制", "礼服", "拍照"],
        "media_urls": ["images/汉服/唐制交领袍1.jpg", "images/汉服/唐制交领袍2.jpg"],
        "price": Decimal("759.00"),
        "member_price": Decimal("699.00"),
        "stock": 10,
    },
    {
        "category_slug": "hanfu",
        "name": "宋风褙子套装",
        "subtitle": "雅致豆绿配色",
        "cover_url": "images/汉服/宋风褙子套装.jpg",
        "description": "轻盈褙子与百迭裙组合，适合春夏穿着。",
        "culture_summary": "宋风服饰强调含蓄雅致，与文人审美密切相关。",
        "dynasty_style": "宋制",
        "craft_type": "绣花",
        "festival_tag": "春夏",
        "scene_tag": "茶会",
        "tags": ["宋制", "褙子", "雅致"],
        "media_urls": ["images/汉服/宋风褙子套装.jpg"],
        "price": Decimal("699.00"),
        "member_price": Decimal("629.00"),
        "stock": 16,
    },
    {
        "category_slug": "wenchuang",
        "name": "故宫宫廷香囊",
        "subtitle": "传统纹样真丝款",
        "cover_url": "images/文创产品/故宫宫廷香囊1.jpg",
        "description": "以宫廷纹样为灵感的香囊，适合节日佩戴。",
        "culture_summary": "香囊兼具装饰与祈福寓意，是传统节俗中的常见物件。",
        "dynasty_style": "宫廷风",
        "craft_type": "刺绣",
        "festival_tag": "端午",
        "scene_tag": "随身",
        "tags": ["香囊", "故宫", "节令"],
        "media_urls": ["images/文创产品/故宫宫廷香囊1.jpg", "images/文创产品/故宫宫廷香囊2.jpg"],
        "price": Decimal("129.00"),
        "member_price": Decimal("109.00"),
        "stock": 30,
    },
    {
        "category_slug": "wenchuang",
        "name": "故宫百喜毯",
        "subtitle": "传统纹样家居款",
        "cover_url": "images/文创产品/故宫百喜毯1.jpg",
        "description": "融合宫廷纹样与现代家居美学的地毯。",
        "culture_summary": "传统吉祥纹样在现代家居中的再设计，是文创转化的重要方式。",
        "dynasty_style": "宫廷风",
        "craft_type": "织毯",
        "festival_tag": "乔迁",
        "scene_tag": "家居",
        "tags": ["家居", "故宫", "吉祥纹样"],
        "media_urls": ["images/文创产品/故宫百喜毯1.jpg", "images/文创产品/故宫百喜毯2.jpg"],
        "price": Decimal("399.00"),
        "member_price": Decimal("359.00"),
        "stock": 14,
    },
    {
        "category_slug": "wenchuang",
        "name": "故宫花神口红",
        "subtitle": "国风彩妆联名款",
        "cover_url": "images/文创产品/故宫花神口红1.jpg",
        "description": "以花神主题设计包装的国风口红。",
        "culture_summary": "宫廷色彩与花卉意象为现代彩妆提供了鲜明的文化符号。",
        "dynasty_style": "宫廷风",
        "craft_type": "彩妆设计",
        "festival_tag": "赠礼",
        "scene_tag": "妆容",
        "tags": ["口红", "花神", "联名"],
        "media_urls": ["images/文创产品/故宫花神口红1.jpg", "images/文创产品/故宫花神口红2.jpg"],
        "price": Decimal("189.00"),
        "member_price": Decimal("169.00"),
        "stock": 25,
    },
    {
        "category_slug": "wenchuang",
        "name": "故宫星空折扇",
        "subtitle": "建筑与星空主题",
        "cover_url": "images/文创产品/故宫星空折扇1.jpg",
        "description": "融合故宫建筑元素与夜空意象的折扇。",
        "culture_summary": "折扇兼具实用与审美，是传统文人器物中的代表之一。",
        "dynasty_style": "明清风",
        "craft_type": "印绘",
        "festival_tag": "夏日",
        "scene_tag": "出行",
        "tags": ["折扇", "故宫", "星空"],
        "media_urls": ["images/文创产品/故宫星空折扇1.jpg", "images/文创产品/故宫星空折扇2.jpg"],
        "price": Decimal("99.00"),
        "member_price": Decimal("89.00"),
        "stock": 40,
    },
    {
        "category_slug": "feiyi",
        "name": "景泰蓝花瓶",
        "subtitle": "掐丝珐琅工艺",
        "cover_url": "images/非遗手工艺/景泰蓝花瓶1.jpg",
        "description": "景泰蓝小花瓶，适合作为案头陈设。",
        "culture_summary": "景泰蓝以金属胎体与珐琅填彩著称，是宫廷工艺的重要代表。",
        "dynasty_style": "宫廷风",
        "craft_type": "景泰蓝",
        "festival_tag": "陈设",
        "scene_tag": "家居",
        "tags": ["景泰蓝", "花瓶", "陈设"],
        "media_urls": ["images/非遗手工艺/景泰蓝花瓶1.jpg", "images/非遗手工艺/景泰蓝花瓶2.jpg"],
        "price": Decimal("599.00"),
        "member_price": Decimal("549.00"),
        "stock": 8,
    },
    {
        "category_slug": "feiyi",
        "name": "绒花胸针",
        "subtitle": "南京绒花灵感款",
        "cover_url": "images/非遗手工艺/绒花胸针1.jpg",
        "description": "小巧精致的绒花胸针，适合点缀衣襟。",
        "culture_summary": "绒花是南京传统手工艺，以色彩丰富和立体花型著称。",
        "dynasty_style": "民艺风",
        "craft_type": "绒花",
        "festival_tag": "赠礼",
        "scene_tag": "穿搭",
        "tags": ["绒花", "胸针", "非遗"],
        "media_urls": ["images/非遗手工艺/绒花胸针1.jpg", "images/非遗手工艺/绒花胸针2.jpg"],
        "price": Decimal("169.00"),
        "member_price": Decimal("149.00"),
        "stock": 22,
    },
    {
        "category_slug": "feiyi",
        "name": "天官赐福皮影戏礼盒",
        "subtitle": "皮影戏体验套装",
        "cover_url": "images/非遗手工艺/天官赐福皮影戏礼盒1.jpg",
        "description": "集合皮影人偶与展示灯的体验礼盒。",
        "culture_summary": "皮影戏是中国古老戏剧形态之一，兼具戏曲与工艺双重价值。",
        "dynasty_style": "戏曲风",
        "craft_type": "皮影",
        "festival_tag": "节庆",
        "scene_tag": "亲子",
        "tags": ["皮影", "礼盒", "体验"],
        "media_urls": [
            "images/非遗手工艺/天官赐福皮影戏礼盒1.jpg",
            "images/非遗手工艺/天官赐福皮影戏礼盒2.jpg",
        ],
        "price": Decimal("299.00"),
        "member_price": Decimal("269.00"),
        "stock": 11,
    },
    {
        "category_slug": "feiyi",
        "name": "竹编龙舟",
        "subtitle": "手工竹编摆件",
        "cover_url": "images/非遗手工艺/竹编龙舟1.jpg",
        "description": "以竹编工艺制作的龙舟摆件，适合端午陈设。",
        "culture_summary": "竹编工艺强调材料天然与编织秩序，是民艺代表之一。",
        "dynasty_style": "民艺风",
        "craft_type": "竹编",
        "festival_tag": "端午",
        "scene_tag": "陈设",
        "tags": ["竹编", "龙舟", "端午"],
        "media_urls": ["images/非遗手工艺/竹编龙舟1.jpg", "images/非遗手工艺/竹编龙舟2.jpg"],
        "price": Decimal("239.00"),
        "member_price": Decimal("219.00"),
        "stock": 13,
    },
    {
        "category_slug": "accessory",
        "name": "点翠发簪",
        "subtitle": "古风造型点缀",
        "cover_url": "images/饰品/点翠发簪.jpg",
        "description": "仿点翠工艺发簪，适合古风穿搭。",
        "culture_summary": "发簪是传统发饰体系的重要组成部分，兼具固定与装饰作用。",
        "dynasty_style": "宫廷风",
        "craft_type": "金属镶嵌",
        "festival_tag": "拍照",
        "scene_tag": "穿搭",
        "tags": ["发簪", "饰品", "古风"],
        "media_urls": ["images/饰品/点翠发簪.jpg"],
        "price": Decimal("129.00"),
        "member_price": Decimal("109.00"),
        "stock": 35,
    },
    {
        "category_slug": "accessory",
        "name": "玉兔耳坠",
        "subtitle": "中秋限定饰品",
        "cover_url": "images/饰品/玉兔耳坠.jpg",
        "description": "玉兔主题耳坠，轻巧灵动。",
        "culture_summary": "玉兔意象常见于中秋神话叙事，也常被用于吉祥饰物设计。",
        "dynasty_style": "节令风",
        "craft_type": "珐琅",
        "festival_tag": "中秋",
        "scene_tag": "穿搭",
        "tags": ["耳坠", "玉兔", "中秋"],
        "media_urls": ["images/饰品/玉兔耳坠.jpg"],
        "price": Decimal("89.00"),
        "member_price": Decimal("79.00"),
        "stock": 40,
    },
    {
        "category_slug": "accessory",
        "name": "云肩披帛扣",
        "subtitle": "汉服搭配小配件",
        "cover_url": "images/饰品/云肩披帛扣.jpg",
        "description": "适合搭配披帛与云肩的小型金属扣件。",
        "culture_summary": "服饰配件虽小，却承担了整体造型定风格的关键作用。",
        "dynasty_style": "明制",
        "craft_type": "金工",
        "festival_tag": "日常",
        "scene_tag": "穿搭",
        "tags": ["配饰", "云肩", "汉服"],
        "media_urls": ["images/饰品/云肩披帛扣.jpg"],
        "price": Decimal("59.00"),
        "member_price": Decimal("49.00"),
        "stock": 60,
    },
    {
        "category_slug": "accessory",
        "name": "宫灯流苏书签",
        "subtitle": "古风阅读配饰",
        "cover_url": "images/饰品/宫灯流苏书签.jpg",
        "description": "带流苏装饰的宫灯造型书签。",
        "culture_summary": "把宫灯意象转化为书签，是传统器物符号的小型化再设计。",
        "dynasty_style": "宫廷风",
        "craft_type": "金属压铸",
        "festival_tag": "赠礼",
        "scene_tag": "阅读",
        "tags": ["书签", "宫灯", "文房"],
        "media_urls": ["images/饰品/宫灯流苏书签.jpg"],
        "price": Decimal("45.00"),
        "member_price": Decimal("39.00"),
        "stock": 80,
    },
    {
        "category_slug": "gift-box",
        "name": "节气香礼盒",
        "subtitle": "四时闻香套装",
        "cover_url": "images/礼盒/节气香礼盒.jpg",
        "description": "围绕二十四节气设计的闻香礼盒。",
        "culture_summary": "节气礼盒把时间感与仪式感结合，适合做文化礼赠。",
        "dynasty_style": "节令风",
        "craft_type": "调香",
        "festival_tag": "送礼",
        "scene_tag": "礼赠",
        "tags": ["礼盒", "节气", "闻香"],
        "media_urls": ["images/礼盒/节气香礼盒.jpg"],
        "price": Decimal("259.00"),
        "member_price": Decimal("229.00"),
        "stock": 20,
    },
    {
        "category_slug": "gift-box",
        "name": "上元灯会礼盒",
        "subtitle": "节庆氛围套装",
        "cover_url": "images/礼盒/上元灯会礼盒.jpg",
        "description": "集合折扇、流苏与节庆小物的礼盒。",
        "culture_summary": "上元节意象丰富，适合转化为节庆型文创礼盒。",
        "dynasty_style": "节令风",
        "craft_type": "礼盒设计",
        "festival_tag": "元宵",
        "scene_tag": "送礼",
        "tags": ["礼盒", "元宵", "节庆"],
        "media_urls": ["images/礼盒/上元灯会礼盒.jpg"],
        "price": Decimal("319.00"),
        "member_price": Decimal("289.00"),
        "stock": 15,
    },
    {
        "category_slug": "gift-box",
        "name": "国风美妆礼盒",
        "subtitle": "花神主题组合",
        "cover_url": "images/礼盒/国风美妆礼盒.jpg",
        "description": "集合口红、镜盒与香包的组合礼盒。",
        "culture_summary": "国风美妆礼盒把传统审美主题转化成现代消费品组合。",
        "dynasty_style": "宫廷风",
        "craft_type": "礼盒设计",
        "festival_tag": "送礼",
        "scene_tag": "妆容",
        "tags": ["礼盒", "美妆", "花神"],
        "media_urls": ["images/礼盒/国风美妆礼盒.jpg"],
        "price": Decimal("399.00"),
        "member_price": Decimal("359.00"),
        "stock": 12,
    },
    {
        "category_slug": "gift-box",
        "name": "端午祈福礼盒",
        "subtitle": "香囊与竹编主题",
        "cover_url": "images/礼盒/端午祈福礼盒.jpg",
        "description": "端午主题礼盒，适合节日送礼与家居陈设。",
        "culture_summary": "端午器物常承载祈福、辟邪与团聚等传统寓意。",
        "dynasty_style": "节令风",
        "craft_type": "礼盒设计",
        "festival_tag": "端午",
        "scene_tag": "礼赠",
        "tags": ["礼盒", "端午", "祈福"],
        "media_urls": ["images/礼盒/端午祈福礼盒.jpg"],
        "price": Decimal("289.00"),
        "member_price": Decimal("259.00"),
        "stock": 17,
    },
]


def seed_member_levels(session: Session) -> int:
    existing_levels = {
        level.code: level
        for level in session.scalars(
            select(MemberLevel).order_by(MemberLevel.level_order.asc())
        ).all()
    }

    for level_seed in MEMBER_LEVEL_SEEDS:
        level = existing_levels.get(level_seed["code"])
        if level is None:
            level = MemberLevel(code=level_seed["code"])
            session.add(level)

        level.name = level_seed["name"]
        level.level_order = level_seed["level_order"]
        level.min_points = level_seed["min_points"]
        level.discount_rate = level_seed["discount_rate"]
        level.points_rate = level_seed["points_rate"]
        level.description = level_seed["description"]
        level.is_default = level_seed["is_default"]

    session.flush()
    return session.query(MemberLevel).count()


def seed_default_admin_user(session: Session) -> int:
    existing_admin = session.scalar(
        select(AdminUser).where(AdminUser.email == DEFAULT_ADMIN_USER["email"])
    )
    if existing_admin is None:
        session.add(
            AdminUser(
                email=DEFAULT_ADMIN_USER["email"],
                username=DEFAULT_ADMIN_USER["username"],
                password_hash=hash_password(DEFAULT_ADMIN_USER["password"]),
                role=DEFAULT_ADMIN_USER["role"],
                is_active=True,
            )
        )
        session.flush()

    return session.query(AdminUser).count()


def seed_categories(session: Session) -> dict[str, Category]:
    existing_categories = {
        category.slug: category
        for category in session.scalars(select(Category)).all()
    }
    categories_by_slug: dict[str, Category] = {}

    for index, category_data in enumerate(CATEGORY_SEEDS, start=1):
        category = existing_categories.get(category_data["slug"])
        if category is None:
            category = Category(slug=category_data["slug"])
            session.add(category)

        category.name = category_data["name"]
        category.description = category_data["description"]
        category.sort_order = index
        category.is_active = True
        categories_by_slug[category.slug] = category

    session.flush()
    return categories_by_slug


def sync_product_media(product: Product, media_urls: list[str]) -> None:
    product.media_items = [
        ProductMedia(media_type="image", url=media_url, sort_order=media_index)
        for media_index, media_url in enumerate(media_urls, start=1)
    ]


def sync_product_tags(product: Product, tags: list[str]) -> None:
    product.tags = [ProductTag(tag=tag) for tag in tags]


def sync_default_sku(
    product: Product,
    *,
    index: int,
    product_name: str,
    price: Decimal,
    member_price: Decimal,
    stock: int,
) -> None:
    sku_code = f"SKU-{index:03d}"
    sku = next((item for item in product.skus if item.sku_code == sku_code), None)
    if sku is None:
        sku = product.default_sku
    if sku is None:
        sku = ProductSku(sku_code=sku_code)
        product.skus.append(sku)

    sku.sku_code = sku_code
    sku.name = f"{product_name} 默认款"
    sku.specs_json = {"default": True}
    sku.price = price
    sku.member_price = member_price
    sku.is_default = True
    sku.is_active = True

    if sku.inventory is None:
        sku.inventory = Inventory(quantity=stock)
    else:
        sku.inventory.quantity = stock

    for existing_sku in product.skus:
        if existing_sku is not sku:
            existing_sku.is_default = False


def seed_base_data(session: Session) -> dict[str, int]:
    admin_user_count = seed_default_admin_user(session)
    member_level_count = seed_member_levels(session)
    categories_by_slug = seed_categories(session)
    products_by_name = {
        product.name: product for product in session.scalars(select(Product)).all()
    }

    for index, product_data in enumerate(PRODUCT_SEEDS, start=1):
        product = products_by_name.get(product_data["name"])
        if product is None:
            product = Product(name=product_data["name"])
            session.add(product)
            products_by_name[product.name] = product

        product.category = categories_by_slug[product_data["category_slug"]]
        product.subtitle = product_data["subtitle"]
        product.cover_url = product_data["cover_url"]
        product.description = product_data["description"]
        product.culture_summary = product_data["culture_summary"]
        product.dynasty_style = product_data["dynasty_style"]
        product.craft_type = product_data["craft_type"]
        product.festival_tag = product_data["festival_tag"]
        product.scene_tag = product_data["scene_tag"]
        product.status = 1

        sync_default_sku(
            product,
            index=index,
            product_name=product_data["name"],
            price=product_data["price"],
            member_price=product_data["member_price"],
            stock=product_data["stock"],
        )
        sync_product_media(product, product_data["media_urls"])
        sync_product_tags(product, product_data["tags"])

    session.commit()
    return {
        "admin_users": admin_user_count,
        "member_levels": member_level_count,
        "categories": session.query(Category).count(),
        "products": session.query(Product).count(),
    }


def main() -> None:
    session = get_session_factory()()
    try:
        result = seed_base_data(session)
        print(
            "Seeded"
            f" admin_users={result['admin_users']}"
            f" member_levels={result['member_levels']}"
            f" categories={result['categories']}"
            f" products={result['products']}"
        )
    finally:
        session.close()


if __name__ == "__main__":
    main()
