from flask import Blueprint, request, jsonify
from config import get_connection
import random, string
from datetime import datetime, timedelta

dat_ve_bp = Blueprint('dat_ve', __name__)

def tao_ma_dat_ve():
    return 'BKG' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))

# Tạo đơn đặt vé
@dat_ve_bp.route('/tao', methods=['POST'])
def tao_dat_ve():
    data = request.json
    khach_hang_id = data.get('khach_hang_id')
    loai_chuyen   = data.get('loai_chuyen', 'Mot_chieu')
    danh_sach_ve  = data.get('ve', [])

    if not khach_hang_id or not danh_sach_ve:
        return jsonify({'error': 'Thiếu thông tin đặt vé'}), 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        tong_tien = sum(int(v.get('gia_ve', 0)) for v in danh_sach_ve)
        ma_dat_ve = tao_ma_dat_ve()
        het_han   = datetime.now() + timedelta(minutes=30)

        cursor.execute("""
            INSERT INTO dat_ve (khach_hang_id, ma_dat_ve, loai_chuyen, tong_tien, het_han_thanh_toan)
            VALUES (%s, %s, %s, %s, %s)
        """, (khach_hang_id, ma_dat_ve, loai_chuyen, tong_tien, het_han))
        dat_ve_id = cursor.lastrowid

        for v in danh_sach_ve:
            ma_ve = 'TK' + ''.join(random.choices(string.digits, k=8))
            cursor.execute("""
                INSERT INTO ve (dat_ve_id, chuyen_bay_id, hang_ghe_id, loai_hanh_khach,
                                ho_ten, ngay_sinh, gioi_tinh, gia_ve, ma_ve)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                dat_ve_id, v.get('chuyen_bay_id'), v.get('hang_ghe_id'),
                v.get('loai_hanh_khach', 'Nguoi_lon'), v.get('ho_ten'),
                v.get('ngay_sinh'), v.get('gioi_tinh'), v.get('gia_ve'), ma_ve
            ))
            cursor.execute("""
                UPDATE hang_ghe SET so_ghe_con_lai = so_ghe_con_lai - 1 WHERE id = %s
            """, (v.get('hang_ghe_id'),))

        conn.commit()
        return jsonify({
            'success': True,
            'dat_ve_id': dat_ve_id,
            'ma_dat_ve': ma_dat_ve,
            'tong_tien': tong_tien,
            'het_han_thanh_toan': str(het_han)
        })

    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


# Xem chi tiết đơn đặt vé
@dat_ve_bp.route('/<ma_dat_ve>', methods=['GET'])
def xem_dat_ve(ma_dat_ve):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT dv.*, kh.ho_ten AS ten_khach, kh.email
        FROM dat_ve dv
        JOIN khach_hang kh ON dv.khach_hang_id = kh.id
        WHERE dv.ma_dat_ve = %s
    """, (ma_dat_ve,))
    don = cursor.fetchone()

    if not don:
        return jsonify({'error': 'Không tìm thấy đơn đặt vé'}), 404

    cursor.execute("""
        SELECT v.*, cb.so_hieu_cb, hhk.ten_hang,
               sb_di.ma_iata AS tu, sb_den.ma_iata AS den,
               cb.gio_cat_canh, cb.gio_ha_canh, cb.thoi_gian_bay,
               hg.ten_hang AS hang_ghe
        FROM ve v
        JOIN chuyen_bay cb ON v.chuyen_bay_id = cb.id
        JOIN hang_hang_khong hhk ON cb.hang_hk_id = hhk.id
        JOIN tuyen_duong td ON cb.tuyen_duong_id = td.id
        JOIN san_bay sb_di  ON td.san_bay_di_id  = sb_di.id
        JOIN san_bay sb_den ON td.san_bay_den_id = sb_den.id
        JOIN hang_ghe hg    ON v.hang_ghe_id     = hg.id
        WHERE v.dat_ve_id = %s
    """, (don['id'],))
    ve_list = cursor.fetchall()

    for v in ve_list:
        v['gio_cat_canh'] = str(v['gio_cat_canh'])
        v['gio_ha_canh']  = str(v['gio_ha_canh'])
        if v.get('ngay_sinh'):
            v['ngay_sinh'] = str(v['ngay_sinh'])

    don['ngay_dat'] = str(don['ngay_dat'])
    if don.get('het_han_thanh_toan'):
        don['het_han_thanh_toan'] = str(don['het_han_thanh_toan'])

    don['ve'] = ve_list
    cursor.close()
    conn.close()
    return jsonify(don)


# Hủy vé
@dat_ve_bp.route('/huy/<ma_dat_ve>', methods=['PUT'])
def huy_ve(ma_dat_ve):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, trang_thai FROM dat_ve WHERE ma_dat_ve = %s", (ma_dat_ve,))
        don = cursor.fetchone()

        if not don:
            return jsonify({'error': 'Không tìm thấy đơn đặt vé'}), 404
        if don['trang_thai'] == 'da_huy':
            return jsonify({'error': 'Vé đã được hủy trước đó'}), 400

        # Hoàn lại ghế
        cursor.execute("SELECT hang_ghe_id FROM ve WHERE dat_ve_id = %s", (don['id'],))
        ve_list = cursor.fetchall()
        for v in ve_list:
            cursor.execute("UPDATE hang_ghe SET so_ghe_con_lai = so_ghe_con_lai + 1 WHERE id = %s", (v['hang_ghe_id'],))

        cursor.execute("UPDATE dat_ve SET trang_thai = 'da_huy' WHERE id = %s", (don['id'],))
        cursor.execute("UPDATE ve SET trang_thai = 'da_huy' WHERE dat_ve_id = %s", (don['id'],))
        conn.commit()
        return jsonify({'success': True, 'message': 'Hủy vé thành công!'})

    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()
