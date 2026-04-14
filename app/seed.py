from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import MenuItem


DEFAULT_MENU = [
    {"name": "Regular Chai", "category": "Chai", "price": 20, "aliases": "chai,regular tea"},
    {"name": "Ginger Chai", "category": "Chai", "price": 25, "aliases": "ginger chai,adrak chai"},
    {"name": "Ginger Chai Large", "category": "Chai", "price": 40, "aliases": "ginger chai large,big ginger chai"},
    {"name": "Elaichi Chai", "category": "Chai", "price": 25, "aliases": "elaichi chai,cardamom chai"},
    {"name": "Masala Chai", "category": "Chai", "price": 30, "aliases": "masala chai,spiced chai"},
    {"name": "Pudina Chai", "category": "Chai", "price": 30, "aliases": "pudina chai,mint chai"},
    {"name": "Ginger And Mint Chai", "category": "Chai", "price": 30, "aliases": "ginger mint chai,ginger and mint chai"},
    {"name": "Pudina Tea", "category": "Chai Without Milk", "price": 20, "aliases": "pudina tea,mint tea"},
    {"name": "Black Tea", "category": "Chai Without Milk", "price": 20, "aliases": "black tea"},
    {"name": "Black Tea With Ginger", "category": "Chai Without Milk", "price": 25, "aliases": "black tea ginger,ginger black tea"},
    {"name": "Lemon Tea", "category": "Chai Without Milk", "price": 20, "aliases": "lemon tea"},
    {"name": "Lemon Tea With Honey", "category": "Chai Without Milk", "price": 25, "aliases": "honey lemon tea,lemon honey tea"},
    {"name": "Ginger And Pudina Tea", "category": "Chai Without Milk", "price": 25, "aliases": "ginger pudina tea,ginger mint tea no milk"},
    {"name": "Masala Lemon Tea", "category": "Chai Without Milk", "price": 25, "aliases": "masala lemon tea"},
    {"name": "Masala Lemon Honey Tea", "category": "Chai Without Milk", "price": 30, "aliases": "masala lemon honey tea"},
    {"name": "Ginger And Lemon Tea", "category": "Chai Without Milk", "price": 25, "aliases": "ginger lemon tea"},
    {"name": "Ginger Lemon Tea With Honey", "category": "Chai Without Milk", "price": 30, "aliases": "ginger lemon honey tea"},
    {"name": "Green Tea With Honey", "category": "Green Tea", "price": 25, "aliases": "green tea honey,honey green tea"},
    {"name": "Green Ginger Tea With Honey", "category": "Green Tea", "price": 30, "aliases": "green ginger tea,green ginger honey tea"},
    {"name": "Green Tea With Masala And Honey", "category": "Green Tea", "price": 35, "aliases": "green masala tea,green tea masala honey"},
    {"name": "Black Coffee", "category": "Coffee", "price": 20, "aliases": "black coffee"},
    {"name": "Milk Coffee", "category": "Coffee", "price": 25, "aliases": "coffee,milk coffee"},
    {"name": "Black Ginger Coffee", "category": "Coffee", "price": 25, "aliases": "ginger coffee,black ginger coffee"},
    {"name": "Samosa", "category": "Snacks", "price": 20, "aliases": "samosa"},
    {"name": "Bun Maska", "category": "Snacks", "price": 40, "aliases": "bun maska,small bun maska"},
    {"name": "Bun Maska Large", "category": "Snacks", "price": 50, "aliases": "bun maska large,big bun maska"},
    {"name": "Bun Maska Jam", "category": "Snacks", "price": 50, "aliases": "jam bun maska,bun jam"},
    {"name": "Bun Maska Nutella", "category": "Snacks", "price": 50, "aliases": "nutella bun maska"},
    {"name": "Bun Maska Peanut Butter", "category": "Snacks", "price": 50, "aliases": "peanut butter bun maska"},
    {"name": "Bun Samosa", "category": "Snacks", "price": 50, "aliases": "bun samosa"},
    {"name": "Bun Maska Bhujia", "category": "Snacks", "price": 50, "aliases": "bhujia bun maska"},
    {"name": "Plain Maggi", "category": "Maggi", "price": 50, "aliases": "maggi,plain maggi"},
    {"name": "Cheese Maggi", "category": "Maggi", "price": 60, "aliases": "cheese maggi"},
    {"name": "Vegetable Maggi", "category": "Maggi", "price": 70, "aliases": "veg maggi,vegetable maggi"},
    {"name": "Vegetable Cheese Maggi", "category": "Maggi", "price": 80, "aliases": "veg cheese maggi,vegetable cheese maggi"},
    {"name": "Badam Milk", "category": "Milk", "price": 25, "aliases": "badam milk,almond milk"},
    {"name": "Boost", "category": "Milk", "price": 25, "aliases": "boost"},
    {"name": "Horlicks", "category": "Milk", "price": 25, "aliases": "horlicks"},
    {"name": "Bournvita", "category": "Milk", "price": 25, "aliases": "bournvita"},
    {"name": "Hot Chocolate", "category": "Milk", "price": 50, "aliases": "hot chocolate"},
    {"name": "Nimbu Pani", "category": "Mocktails", "price": 50, "aliases": "nimbu pani,lemon soda"},
    {"name": "Jal Jeera", "category": "Mocktails", "price": 60, "aliases": "jal jeera"},
    {"name": "Masala Cola", "category": "Mocktails", "price": 70, "aliases": "masala cola"},
]


def seed_menu(db: Session) -> None:
    existing_items = {
        item.name: item
        for item in db.scalars(select(MenuItem))
    }

    for item in existing_items.values():
        item.is_available = False

    for idx, item in enumerate(DEFAULT_MENU, start=1):
        menu_item = existing_items.get(item["name"])
        if menu_item:
            menu_item.category = item["category"]
            menu_item.price = item["price"]
            menu_item.aliases = item["aliases"]
            menu_item.display_order = idx
            menu_item.is_available = True
        else:
            db.add(
                MenuItem(
                    name=item["name"],
                    category=item["category"],
                    price=item["price"],
                    aliases=item["aliases"],
                    display_order=idx,
                    is_available=True,
                )
            )

    db.commit()
