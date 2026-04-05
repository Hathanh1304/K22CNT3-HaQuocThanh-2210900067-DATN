from flask import Blueprint, request, jsonify
from config import get_connection
from datetime import datetime

ho_tro_bp = Blueprint('ho_tro', __name__)

# Khách hàng gửi yêu cầu
@ho_tro_bp.route('/gui', methods=['POST'])
def gui_yeu_cau():
    data = request.json
    conn = get_connection()
    if not conn:
        return jsonify({'error': 'Không kết nối được database'}), 500
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO ho_tro
              (khach_hang_id, dat_ve_id, ho_ten, email, so_dien_thoai, loai, tieu_de, noi_dung)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            data.get('khach_hang_id'),
            data.get('dat_ve_id'),
            data.get('ho_ten'),
            data.get('email'),
            data.get('so_dien_thoai'),
            data.get('loai', 'hoi_thong_tin'),
            data.get('tieu_de'),
            data.get('noi_dung')
        ))
        conn.commit()
        return jsonify({'success': True, 'id': cursor.lastrowid})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# Khách hàng xem yêu cầu của mình
@ho_tro_bp.route('/cua-toi/<int:kh_id>', methods=['GET'])
def yeu_cau_cua_toi(kh_id):
    conn = get_connection()
    if not conn:
        return jsonify({'error': 'Không kết nối được database'}), 500
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT * FROM ho_tro
            WHERE khach_hang_id = %s
            ORDER BY ngay_gui DESC
        """, (kh_id,))
        data = cursor.fetchall()
        for d in data:
            d['ngay_gui']   = str(d['ngay_gui'])
            d['ngay_xu_ly'] = str(d['ngay_xu_ly']) if d['ngay_xu_ly'] else None
        return jsonify(data)
    finally:
        cursor.close()
        conn.close()

# Admin lấy danh sách hỗ trợ
@ho_tro_bp.route('/admin/danh-sach', methods=['GET'])
def admin_danh_sach():
    trang_thai = request.args.get('trang_thai', '')
    conn = get_connection()
    if not conn:
        return jsonify({'error': 'Không kết nối được database'}), 500
    cursor = conn.cursor(dictionary=True)
    try:
        if trang_thai:
            cursor.execute("""
                SELECT ht.*, kh.ho_ten AS ten_khach_hang
                FROM ho_tro ht
                LEFT JOIN khach_hang kh ON ht.khach_hang_id = kh.id
                WHERE ht.trang_thai = %s
                ORDER BY ht.ngay_gui DESC
            """, (trang_thai,))
        else:
            cursor.execute("""
                SELECT ht.*, kh.ho_ten AS ten_khach_hang
                FROM ho_tro ht
                LEFT JOIN khach_hang kh ON ht.khach_hang_id = kh.id
                ORDER BY ht.ngay_gui DESC
            """)
        data = cursor.fetchall()
        for d in data:
            d['ngay_gui']   = str(d['ngay_gui'])
            d['ngay_xu_ly'] = str(d['ngay_xu_ly']) if d['ngay_xu_ly'] else None
        return jsonify(data)
    finally:
        cursor.close()
        conn.close()

# Admin trả lời + cập nhật trạng thái
@ho_tro_bp.route('/admin/tra-loi/<int:ht_id>', methods=['PUT'])
def admin_tra_loi(ht_id):
    data      = request.json
    phan_hoi  = data.get('phan_hoi', '')
    trang_thai= data.get('trang_thai', 'da_xu_ly')

    conn = get_connection()
    if not conn:
        return jsonify({'error': 'Không kết nối được database'}), 500
    cursor = conn.cursor()
    try:
        # Cập nhật phản hồi VÀ trạng thái
        cursor.execute("""
            UPDATE ho_tro
            SET phan_hoi  = %s,
                trang_thai = %s,
                ngay_xu_ly = %s
            WHERE id = %s
        """, (
            phan_hoi,
            trang_thai,
            datetime.now() if trang_thai in ('da_xu_ly', 'dong') else None,
            ht_id
        ))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'error': 'Không tìm thấy yêu cầu'}), 404
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# Chỉ cập nhật trạng thái (không cần phản hồi)
@ho_tro_bp.route('/admin/cap-nhat-trang-thai/<int:ht_id>', methods=['PUT'])
def cap_nhat_trang_thai(ht_id):
    data       = request.json
    trang_thai = data.get('trang_thai')
    conn = get_connection()
    if not conn:
        return jsonify({'error': 'Không kết nối được database'}), 500
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE ho_tro SET trang_thai = %s,
                ngay_xu_ly = %s
            WHERE id = %s
        """, (
            trang_thai,
            datetime.now() if trang_thai in ('da_xu_ly', 'dong') else None,
            ht_id
        ))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()