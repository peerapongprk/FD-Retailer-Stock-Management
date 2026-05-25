"""Column name constants for RetailIQ."""

class MAKRO:
    LOC_NUM    = "Loc Number"
    MONTH      = "Month"
    DATE       = "Date"
    CUST_GROUP = "Customer Main Group Name"
    CUST_TYPE  = "Customer Type Name"
    CUSTOMER   = "Customer Name"
    CUST_NUM   = "Customer Number"
    DIVISION   = "Division"
    DEPT       = "Department"
    CLASS      = "Class"
    ITEM       = "Item"
    QTY        = "Net Sales Qty"
    REVENUE    = "Net Sales Amt"
    PROFIT     = "Net Profit"

FD_RETAILER_GROUP = "FD RETAILER"

DAY_TH = ["จันทร์","อังคาร","พุธ","พฤหัส","ศุกร์","เสาร์","อาทิตย์"]

class RFM:
    CHAMPION  = "Champion"
    LOYAL     = "Loyal"
    PROMISING = "Promising"
    AT_RISK   = "At Risk"
    CHURNING  = "Churning"
    NEW       = "New"

RFM_COLOR = {
    RFM.CHAMPION:  "#0f7b55",
    RFM.LOYAL:     "#1a6faf",
    RFM.PROMISING: "#7c4dbd",
    RFM.AT_RISK:   "#c07a00",
    RFM.CHURNING:  "#c0392b",
    RFM.NEW:       "#5a6a7a",
}

RFM_ADVICE = {
    RFM.CHAMPION:  "แนะนำสินค้าใหม่ / Bundle deal",
    RFM.LOYAL:     "รักษา — เสนอส่วนลด Tier สูงขึ้น",
    RFM.PROMISING: "เพิ่ม Category ใหม่ให้ลอง",
    RFM.AT_RISK:   "โทรเช็คด่วน — มีสัญญาณลดซื้อ",
    RFM.CHURNING:  "แจ้งเตือนวิกฤต — ใกล้หายไป",
    RFM.NEW:       "แนะนำ Starter Pack สินค้า High-turn",
}
