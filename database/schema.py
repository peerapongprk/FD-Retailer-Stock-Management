"""Column name constants for RetailIQ — maps to Makro Sales By Items export."""

class MAKRO:
    LOC_NUM    = "Loc Number"
    MONTH      = "Month"
    CUST_GROUP = "Customer Main Group Name"
    CUST_TYPE  = "Customer Type Name"
    CUSTOMER   = "Customer Name"
    CUST_NUM   = "Customer Number"
    DIVISION   = "Division"
    DEPT       = "Department"
    CLASS      = "Class"
    ITEM       = "Item"
    REVENUE    = "Net Sales Amt"
    PROFIT     = "Net Profit"

# FD Retailer group filter
FD_RETAILER_GROUP = "FD RETAILER"

# High-velocity classes for OOS prediction (top classes by revenue)
HIGH_VELOCITY_CLASSES = [
    "RTD TEA", "SOFT DRINK", "INSTANT_NOODLES", "ENERGY DRINK",
    "JUICE", "WATER", "LOCAL BEER", "UHT", "SOY BEAN MILK",
    "FUNCTIONAL DRINK", "SPIRIT & HARD LIQUOR (LOCAL)",
    "Vegetable oil", "WHITE SUGAR", "DETERGENT", "SOAP",
    "EXTRUDED & RICE CRACKER", "POTATO CHIPS",
]

# RFM segment labels
class RFM:
    CHAMPION   = "Champion"
    LOYAL      = "Loyal"
    PROMISING  = "Promising"
    AT_RISK    = "At Risk"
    CHURNING   = "Churning"
    NEW        = "New"

RFM_COLOR = {
    RFM.CHAMPION:  "#10b981",
    RFM.LOYAL:     "#3b82f6",
    RFM.PROMISING: "#8b5cf6",
    RFM.AT_RISK:   "#f59e0b",
    RFM.CHURNING:  "#ef4444",
    RFM.NEW:       "#6b7280",
}

RFM_ADVICE = {
    RFM.CHAMPION:  "แนะนำสินค้าใหม่ / Bundle deal",
    RFM.LOYAL:     "รักษา — เสนอส่วนลด Tier สูงขึ้น",
    RFM.PROMISING: "เพิ่ม Category ใหม่ให้ลอง",
    RFM.AT_RISK:   "โทรเช็คด่วน — มีสัญญาณลดซื้อ",
    RFM.CHURNING:  "แจ้งเตือนวิกฤต — ใกล้หายไป",
    RFM.NEW:       "แนะนำ Starter Pack สินค้า High-turn",
}
