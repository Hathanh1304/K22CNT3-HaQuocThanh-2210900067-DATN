from flask import Blueprint, request, jsonify
from config import get_connection

chuyen_bay_bp = Blueprint('chuyen_bay', __name__)

@chuyen_bay_bp.route('/tim-kiem', methods=['GET'])
def tim_kiem():
    san_bay_di    = request.args.get('tu')
    san_bay_den   = request.args.get('den')
    ngay_di       = request.args.get('ngay')
    hang_ghe      = request.args.get('hang', 'Pho_thong')
    so_hanh_khach = request.args.get('so_hk', 1)
    loai_tuyen    = request.args.get('loai_tuyen', '')  # noi_dia hoặc quoc_te

    if not san_bay_di or not san_bay_den or not ngay_di:
        return jsonify({'error': 'Thiếu thông tin tìm kiếm'}), 400

    conn = get_connection()
    if not conn:
        return jsonify({'error': 'Không kết nối được database'}), 500

    cursor = conn.cursor(dictionary=True)
    sql = """
        SELECT cb.id, cb.so_hieu_cb, hhk.ten_hang, hhk.ma_hang,
               sb_di.ma_iata AS san_bay_di, sb_di.thanh_pho AS thanh_pho_di,
               sb_den.ma_iata AS san_bay_den, sb_den.thanh_pho AS thanh_pho_den,
               cb.gio_cat_canh, cb.gio_ha_canh, cb.thoi_gian_bay,
               hg.ten_hang AS hang_ghe, hg.gia_nguoi_lon, hg.gia_tre_em,
               hg.so_ghe_con_lai, hg.han_hanh_ly_kg, hg.id AS hang_ghe_id,
               td.loai_tuyen
        FROM chuyen_bay cb
        JOIN hang_hang_khong hhk ON cb.hang_hk_id     = hhk.id
        JOIN tuyen_duong td       ON cb.tuyen_duong_id = td.id
        JOIN san_bay sb_di        ON td.san_bay_di_id  = sb_di.id
        JOIN san_bay sb_den       ON td.san_bay_den_id = sb_den.id
        JOIN hang_ghe hg          ON hg.chuyen_bay_id  = cb.id
        WHERE sb_di.ma_iata  = %s
          AND sb_den.ma_iata = %s
          AND DATE(cb.gio_cat_canh) = %s
          AND hg.ten_hang = %s
          AND hg.so_ghe_con_lai >= %s
          AND cb.trang_thai = 'du_kien'
          AND (%s = '' OR td.loai_tuyen = %s)
        ORDER BY hg.gia_nguoi_lon ASC
    """
    cursor.execute(sql, (
        san_bay_di, san_bay_den, ngay_di,
        hang_ghe, so_hanh_khach,
        loai_tuyen, loai_tuyen
    ))
    ket_qua = cursor.fetchall()

    for cb in ket_qua:
        cb['gio_cat_canh'] = str(cb['gio_cat_canh'])
        cb['gio_ha_canh']  = str(cb['gio_ha_canh'])

    cursor.close()
    conn.close()
    return jsonify(ket_qua)


# Lấy tất cả sân bay
@chuyen_bay_bp.route('/san-bay', methods=['GET'])
def danh_sach_san_bay():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT ma_iata, ten_san_bay, thanh_pho, quoc_gia FROM san_bay ORDER BY quoc_gia, thanh_pho")
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(data)


# Lấy sân bay nội địa
@chuyen_bay_bp.route('/san-bay/noi-dia', methods=['GET'])
def san_bay_noi_dia():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT ma_iata, ten_san_bay, thanh_pho, quoc_gia
        FROM san_bay WHERE quoc_gia = 'Việt Nam'
        ORDER BY thanh_pho
    """)
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(data)


# Lấy sân bay quốc tế
@chuyen_bay_bp.route('/san-bay/quoc-te', methods=['GET'])
def san_bay_quoc_te():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT ma_iata, ten_san_bay, thanh_pho, quoc_gia
        FROM san_bay WHERE quoc_gia != 'Việt Nam'
        ORDER BY quoc_gia, thanh_pho
    """)
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(data)