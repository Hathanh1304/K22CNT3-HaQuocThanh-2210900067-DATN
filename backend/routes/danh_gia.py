from flask import Blueprint, request, jsonify
from config import get_connection

danh_gia_bp = Blueprint('danh_gia', __name__)

# Khách hàng gửi đánh giá
@danh_gia_bp.route('/gui', methods=['POST'])
def gui_danh_gia():
    data          = request.json
    khach_hang_id = data.get('khach_hang_id')
    chuyen_bay_id = data.get('chuyen_bay_id')
    dat_ve_id     = data.get('dat_ve_id')
    so_sao        = data.get('so_sao', 5)
    tieu_de       = data.get('tieu_de', '')
    noi_dung      = data.get('noi_dung', '')
    dung_gio      = int(data.get('dung_gio', 1))
    ve_sinh       = int(data.get('ve_sinh', 1))
    phuc_vu       = int(data.get('phuc_vu', 1))

    if not khach_hang_id or not chuyen_bay_id or not dat_ve_id:
        return jsonify({'error': 'Thiếu thông tin đánh giá'}), 400
    if not (1 <= int(so_sao) <= 5):
        return jsonify({'error': 'Số sao phải từ 1 đến 5'}), 400

    conn = get_connection()
    if not conn:
        return jsonify({'error': 'Không kết nối được database'}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        # Kiểm tra đã đánh giá chưa
        cursor.execute("""
            SELECT id FROM danh_gia
            WHERE khach_hang_id = %s AND chuyen_bay_id = %s
        """, (khach_hang_id, chuyen_bay_id))
        if cursor.fetchone():
            return jsonify({'error': 'Bạn đã đánh giá chuyến bay này rồi!'}), 400

        # Kiểm tra đơn đặt vé hợp lệ
        cursor.execute("""
            SELECT id FROM dat_ve
            WHERE id = %s AND khach_hang_id = %s AND trang_thai IN ('da_xac_nhan','da_thanh_toan')
        """, (dat_ve_id, khach_hang_id))
        if not cursor.fetchone():
            return jsonify({'error': 'Đơn đặt vé không hợp lệ để đánh giá'}), 400

        cursor.execute("""
            INSERT INTO danh_gia
              (khach_hang_id, chuyen_bay_id, dat_ve_id, so_sao, tieu_de, noi_dung, dung_gio, ve_sinh, phuc_vu)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (khach_hang_id, chuyen_bay_id, dat_ve_id,
              so_sao, tieu_de, noi_dung, dung_gio, ve_sinh, phuc_vu))
        conn.commit()
        return jsonify({'success': True, 'message': 'Đánh giá thành công!'})

    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


# Lấy đánh giá theo chuyến bay
@danh_gia_bp.route('/chuyen-bay/<int:cb_id>', methods=['GET'])
def danh_gia_chuyen_bay(cb_id):
    conn = get_connection()
    if not conn:
        return jsonify({'error': 'Không kết nối được database'}), 500
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT dg.*, kh.ho_ten AS ten_khach,
                   cb.so_hieu_cb
            FROM danh_gia dg
            JOIN khach_hang kh ON dg.khach_hang_id = kh.id
            JOIN chuyen_bay cb ON dg.chuyen_bay_id = cb.id
            WHERE dg.chuyen_bay_id = %s
            ORDER BY dg.ngay_danh_gia DESC
        """, (cb_id,))
        data = cursor.fetchall()
        for d in data:
            d['ngay_danh_gia'] = str(d['ngay_danh_gia'])
        return jsonify(data)
    finally:
        cursor.close()
        conn.close()


# Lấy đánh giá theo đơn đặt vé (để check đã đánh giá chưa)
@danh_gia_bp.route('/kiem-tra/<int:dat_ve_id>', methods=['GET'])
def kiem_tra_danh_gia(dat_ve_id):
    conn = get_connection()
    if not conn:
        return jsonify({'error': 'Không kết nối được database'}), 500
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT dg.* FROM danh_gia dg
            JOIN ve v ON dg.chuyen_bay_id = v.chuyen_bay_id
            WHERE v.dat_ve_id = %s AND dg.dat_ve_id = %s
            LIMIT 1
        """, (dat_ve_id, dat_ve_id))
        result = cursor.fetchone()
        if result:
            result['ngay_danh_gia'] = str(result['ngay_danh_gia'])
        return jsonify({'da_danh_gia': result is not None, 'danh_gia': result})
    finally:
        cursor.close()
        conn.close()


# Admin: lấy tất cả đánh giá
@danh_gia_bp.route('/admin/danh-sach', methods=['GET'])
def admin_danh_sach():
    conn = get_connection()
    if not conn:
        return jsonify({'error': 'Không kết nối được database'}), 500
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT dg.*, kh.ho_ten AS ten_khach, kh.email,
                   cb.so_hieu_cb,
                   sb_di.ma_iata AS tu, sb_den.ma_iata AS den
            FROM danh_gia dg
            JOIN khach_hang kh ON dg.khach_hang_id = kh.id
            JOIN chuyen_bay cb ON dg.chuyen_bay_id = cb.id
            JOIN tuyen_duong td ON cb.tuyen_duong_id = td.id
            JOIN san_bay sb_di  ON td.san_bay_di_id  = sb_di.id
            JOIN san_bay sb_den ON td.san_bay_den_id = sb_den.id
            ORDER BY dg.ngay_danh_gia DESC
        """)
        data = cursor.fetchall()
        for d in data:
            d['ngay_danh_gia'] = str(d['ngay_danh_gia'])
        return jsonify(data)
    finally:
        cursor.close()
        conn.close()


# Admin: xóa đánh giá
@danh_gia_bp.route('/admin/xoa/<int:dg_id>', methods=['DELETE'])
def admin_xoa(dg_id):
    conn = get_connection()
    if not conn:
        return jsonify({'error': 'Không kết nối được database'}), 500
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM danh_gia WHERE id = %s", (dg_id,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()
