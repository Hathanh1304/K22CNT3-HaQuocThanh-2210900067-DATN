from flask import Blueprint, request, jsonify
from config import get_connection

thanh_toan_bp = Blueprint('thanh_toan', __name__)

@thanh_toan_bp.route('/thanh-toan', methods=['POST'])
def thanh_toan():
    data        = request.json
    dat_ve_id   = data.get('dat_ve_id')
    phuong_thuc = data.get('phuong_thuc')
    so_tien     = data.get('so_tien')

    if not dat_ve_id or not phuong_thuc or not so_tien:
        return jsonify({'error': 'Thiếu thông tin thanh toán'}), 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        import random, string
        ma_gd = phuong_thuc.upper() + '-' + ''.join(random.choices(string.digits, k=10))

        cursor.execute("""
            INSERT INTO thanh_toan (dat_ve_id, so_tien, phuong_thuc, trang_thai, ma_giao_dich)
            VALUES (%s, %s, %s, 'thanh_cong', %s)
        """, (dat_ve_id, so_tien, phuong_thuc, ma_gd))

        cursor.execute("""
            UPDATE dat_ve SET trang_thai = 'da_thanh_toan' WHERE id = %s
        """, (dat_ve_id,))

        cursor.execute("""
            UPDATE ve SET trang_thai = 'da_xac_nhan' WHERE dat_ve_id = %s
        """, (dat_ve_id,))

        # ✅ Lấy thông tin đơn đặt vé để tạo thông báo
        cursor.execute("""
            SELECT dv.ma_dat_ve, dv.khach_hang_id, dv.tong_tien, dv.loai_chuyen,
                   v.ho_ten, cb.so_hieu_cb,
                   sb_di.ma_iata AS tu, sb_den.ma_iata AS den,
                   cb.gio_cat_canh
            FROM dat_ve dv
            JOIN ve v ON v.dat_ve_id = dv.id
            JOIN chuyen_bay cb ON v.chuyen_bay_id = cb.id
            JOIN tuyen_duong td ON cb.tuyen_duong_id = td.id
            JOIN san_bay sb_di  ON td.san_bay_di_id  = sb_di.id
            JOIN san_bay sb_den ON td.san_bay_den_id = sb_den.id
            WHERE dv.id = %s
            LIMIT 1
        """, (dat_ve_id,))
        don = cursor.fetchone()

        # ✅ Tạo thông báo cho khách hàng
        if don and don.get('khach_hang_id'):
            gia_fmt = f"{int(so_tien):,}".replace(',', '.') + ' ₫'
            tieu_de = f"✅ Đặt vé thành công - {don['ma_dat_ve']}"
            noi_dung = (
                f"Bạn đã đặt vé thành công chuyến bay {don['so_hieu_cb']} "
                f"({don['tu']} → {don['den']}). "
                f"Tổng tiền: {gia_fmt}. "
                f"Mã giao dịch: {ma_gd}."
            )
            cursor.execute("""
                INSERT INTO thong_bao (khach_hang_id, loai, tieu_de, noi_dung)
                VALUES (%s, 'xac_nhan_ve', %s, %s)
            """, (don['khach_hang_id'], tieu_de, noi_dung))

        conn.commit()
        return jsonify({
            'success': True,
            'ma_giao_dich': ma_gd,
            'message': 'Thanh toán thành công!'
        })

    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@thanh_toan_bp.route('/trang-thai/<int:dat_ve_id>', methods=['GET'])
def trang_thai(dat_ve_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT tt.*, dv.ma_dat_ve, dv.trang_thai AS trang_thai_don
        FROM thanh_toan tt
        JOIN dat_ve dv ON tt.dat_ve_id = dv.id
        WHERE tt.dat_ve_id = %s
    """, (dat_ve_id,))
    data = cursor.fetchone()
    if data:
        data['thoi_gian'] = str(data['thoi_gian'])
    cursor.close()
    conn.close()
    return jsonify(data or {'error': 'Không tìm thấy'})