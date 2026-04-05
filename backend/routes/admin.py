from flask import Blueprint, request, jsonify
from config import get_connection

admin_bp = Blueprint('admin', __name__)

# Dashboard
@admin_bp.route('/dashboard', methods=['GET'])
def dashboard():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT COUNT(*) AS tong FROM khach_hang")
    tong_kh = cursor.fetchone()['tong']
    cursor.execute("SELECT COUNT(*) AS tong FROM dat_ve WHERE trang_thai != 'da_huy'")
    tong_don = cursor.fetchone()['tong']
    cursor.execute("SELECT COUNT(*) AS tong FROM chuyen_bay WHERE trang_thai = 'du_kien'")
    tong_cb = cursor.fetchone()['tong']
    cursor.execute("SELECT COALESCE(SUM(so_tien), 0) AS tong FROM thanh_toan WHERE trang_thai = 'thanh_cong'")
    doanh_thu = cursor.fetchone()['tong']
    cursor.execute("""
        SELECT DATE(ngay_dat) AS ngay, SUM(tong_tien) AS doanh_thu, COUNT(*) AS so_don
        FROM dat_ve WHERE trang_thai IN ('da_thanh_toan','da_xac_nhan')
        GROUP BY DATE(ngay_dat) ORDER BY ngay DESC LIMIT 7
    """)
    doanh_thu_7ngay = cursor.fetchall()
    for d in doanh_thu_7ngay:
        d['ngay'] = str(d['ngay'])
    cursor.close()
    conn.close()
    return jsonify({
        'tong_khach_hang': tong_kh,
        'tong_don_dat_ve': tong_don,
        'tong_chuyen_bay': tong_cb,
        'tong_doanh_thu':  float(doanh_thu),
        'doanh_thu_7ngay': doanh_thu_7ngay
    })

# Danh sách đơn đặt vé
@admin_bp.route('/don-dat-ve', methods=['GET'])
def ds_don_dat_ve():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT dv.id, dv.ma_dat_ve, dv.loai_chuyen, dv.tong_tien,
               dv.trang_thai, dv.ngay_dat,
               kh.ho_ten AS ten_khach, kh.email, kh.so_dien_thoai
        FROM dat_ve dv
        JOIN khach_hang kh ON dv.khach_hang_id = kh.id
        ORDER BY dv.ngay_dat DESC
    """)
    data = cursor.fetchall()
    for d in data:
        d['ngay_dat'] = str(d['ngay_dat'])
    cursor.close()
    conn.close()
    return jsonify(data)

# Danh sách khách hàng
@admin_bp.route('/khach-hang', methods=['GET'])
def ds_khach_hang():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT kh.id, kh.ho_ten, kh.email, kh.so_dien_thoai,
               kh.ngay_tao, COUNT(dv.id) AS so_don
        FROM khach_hang kh
        LEFT JOIN dat_ve dv ON dv.khach_hang_id = kh.id
        GROUP BY kh.id ORDER BY kh.ngay_tao DESC
    """)
    data = cursor.fetchall()
    for d in data:
        d['ngay_tao'] = str(d['ngay_tao'])
    cursor.close()
    conn.close()
    return jsonify(data)

# Danh sách chuyến bay
@admin_bp.route('/chuyen-bay', methods=['GET'])
def ds_chuyen_bay():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT cb.id, cb.so_hieu_cb, hhk.ten_hang,
               sb_di.ma_iata AS tu, sb_den.ma_iata AS den,
               cb.gio_cat_canh, cb.gio_ha_canh, cb.trang_thai,
               SUM(hg.so_ghe_tong) AS tong_ghe,
               SUM(hg.so_ghe_con_lai) AS ghe_trong
        FROM chuyen_bay cb
        JOIN hang_hang_khong hhk ON cb.hang_hk_id = hhk.id
        JOIN tuyen_duong td ON cb.tuyen_duong_id = td.id
        JOIN san_bay sb_di  ON td.san_bay_di_id  = sb_di.id
        JOIN san_bay sb_den ON td.san_bay_den_id = sb_den.id
        LEFT JOIN hang_ghe hg ON hg.chuyen_bay_id = cb.id
        GROUP BY cb.id ORDER BY cb.gio_cat_canh DESC
    """)
    data = cursor.fetchall()
    for d in data:
        d['gio_cat_canh'] = str(d['gio_cat_canh'])
        d['gio_ha_canh']  = str(d['gio_ha_canh'])
    cursor.close()
    conn.close()
    return jsonify(data)

# Cập nhật trạng thái chuyến bay
@admin_bp.route('/chuyen-bay/<int:cb_id>/trang-thai', methods=['PUT'])
def cap_nhat_trang_thai_cb(cb_id):
    data = request.json
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE chuyen_bay SET trang_thai = %s WHERE id = %s", (data.get('trang_thai'), cb_id))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'success': True})

# Thêm chuyến bay
@admin_bp.route('/chuyen-bay/them', methods=['POST'])
def them_chuyen_bay():
    data = request.json
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        san_bay_di  = data.get('san_bay_di')
        san_bay_den = data.get('san_bay_den')
        cursor.execute("""
            SELECT id FROM tuyen_duong
            WHERE san_bay_di_id  = (SELECT id FROM san_bay WHERE ma_iata = %s)
              AND san_bay_den_id = (SELECT id FROM san_bay WHERE ma_iata = %s)
        """, (san_bay_di, san_bay_den))
        tuyen = cursor.fetchone()
        if not tuyen:
            cursor.execute("SELECT quoc_gia FROM san_bay WHERE ma_iata = %s", (san_bay_di,))
            qg_di = cursor.fetchone()
            cursor.execute("SELECT quoc_gia FROM san_bay WHERE ma_iata = %s", (san_bay_den,))
            qg_den = cursor.fetchone()
            loai = 'noi_dia' if (qg_di and qg_den and
                                  qg_di['quoc_gia'] == 'Việt Nam' and
                                  qg_den['quoc_gia'] == 'Việt Nam') else 'quoc_te'
            cursor.execute("""
                INSERT INTO tuyen_duong (san_bay_di_id, san_bay_den_id, khoang_cach_km, loai_tuyen)
                VALUES (
                    (SELECT id FROM san_bay WHERE ma_iata = %s),
                    (SELECT id FROM san_bay WHERE ma_iata = %s),
                    0, %s
                )
            """, (san_bay_di, san_bay_den, loai))
            tuyen_id = cursor.lastrowid
        else:
            tuyen_id = tuyen['id']
        cursor.execute("""
            INSERT INTO chuyen_bay
              (hang_hk_id, tuyen_duong_id, so_hieu_cb, gio_cat_canh, gio_ha_canh, thoi_gian_bay)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            data.get('hang_hk_id'), tuyen_id,
            data.get('so_hieu_cb'), data.get('gio_cat_canh'),
            data.get('gio_ha_canh'), data.get('thoi_gian_bay')
        ))
        cb_id = cursor.lastrowid
        cursor.execute("""
            INSERT INTO hang_ghe
              (chuyen_bay_id, ten_hang, gia_nguoi_lon, gia_tre_em, so_ghe_tong, so_ghe_con_lai)
            VALUES (%s, 'Pho_thong', %s, %s, %s, %s)
        """, (cb_id, data.get('gia_nguoi_lon'), data.get('gia_tre_em'),
              data.get('so_ghe'), data.get('so_ghe')))
        conn.commit()
        return jsonify({'success': True, 'id': cb_id})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# Sửa chuyến bay
@admin_bp.route('/chuyen-bay/sua/<int:cb_id>', methods=['PUT'])
def sua_chuyen_bay(cb_id):
    data = request.json
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            UPDATE chuyen_bay SET
                so_hieu_cb    = %s,
                gio_cat_canh  = %s,
                gio_ha_canh   = %s,
                thoi_gian_bay = %s,
                trang_thai    = %s
            WHERE id = %s
        """, (
            data.get('so_hieu_cb'), data.get('gio_cat_canh'),
            data.get('gio_ha_canh'), data.get('thoi_gian_bay'),
            data.get('trang_thai'), cb_id
        ))
        cursor.execute("""
            UPDATE hang_ghe SET gia_nguoi_lon = %s, gia_tre_em = %s
            WHERE chuyen_bay_id = %s AND ten_hang = 'Pho_thong'
        """, (data.get('gia_nguoi_lon'), data.get('gia_tre_em'), cb_id))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# Lấy chi tiết chuyến bay
@admin_bp.route('/chuyen-bay/chi-tiet/<int:cb_id>', methods=['GET'])
def chi_tiet_chuyen_bay(cb_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT cb.*, hhk.ten_hang, hhk.ma_hang,
               sb_di.ma_iata AS tu, sb_den.ma_iata AS den,
               hg.gia_nguoi_lon, hg.gia_tre_em, hg.so_ghe_tong
        FROM chuyen_bay cb
        JOIN hang_hang_khong hhk ON cb.hang_hk_id = hhk.id
        JOIN tuyen_duong td ON cb.tuyen_duong_id = td.id
        JOIN san_bay sb_di  ON td.san_bay_di_id  = sb_di.id
        JOIN san_bay sb_den ON td.san_bay_den_id = sb_den.id
        LEFT JOIN hang_ghe hg ON hg.chuyen_bay_id = cb.id AND hg.ten_hang = 'Pho_thong'
        WHERE cb.id = %s
    """, (cb_id,))
    data = cursor.fetchone()
    if data:
        data['gio_cat_canh'] = str(data['gio_cat_canh'])
        data['gio_ha_canh']  = str(data['gio_ha_canh'])
    cursor.close()
    conn.close()
    return jsonify(data or {})

# Xóa chuyến bay (cascade đúng thứ tự)
@admin_bp.route('/chuyen-bay/xoa/<int:cb_id>', methods=['DELETE'])
def xoa_chuyen_bay(cb_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # 1. Lấy danh sách hang_ghe
        cursor.execute("SELECT id FROM hang_ghe WHERE chuyen_bay_id = %s", (cb_id,))
        hang_ghes = cursor.fetchall()
        hang_ghe_ids = [h['id'] for h in hang_ghes]

        if hang_ghe_ids:
            fmt = ','.join(['%s'] * len(hang_ghe_ids))
            # 2. Lấy ve thuộc hang_ghe
            cursor.execute(f"SELECT id FROM ve WHERE hang_ghe_id IN ({fmt})", hang_ghe_ids)
            ve_ids = [v['id'] for v in cursor.fetchall()]
            if ve_ids:
                fmt_ve = ','.join(['%s'] * len(ve_ids))
                # 3. Xóa dich_vu_bo_sung
                cursor.execute(f"DELETE FROM dich_vu_bo_sung WHERE ve_id IN ({fmt_ve})", ve_ids)
            # 4. Xóa ve theo hang_ghe
            cursor.execute(f"DELETE FROM ve WHERE hang_ghe_id IN ({fmt})", hang_ghe_ids)

        # 5. Xóa ve theo chuyen_bay_id (nếu còn)
        cursor.execute("SELECT id FROM ve WHERE chuyen_bay_id = %s", (cb_id,))
        ve_cb = [v['id'] for v in cursor.fetchall()]
        if ve_cb:
            fmt_cb = ','.join(['%s'] * len(ve_cb))
            cursor.execute(f"DELETE FROM dich_vu_bo_sung WHERE ve_id IN ({fmt_cb})", ve_cb)
            cursor.execute(f"DELETE FROM ve WHERE id IN ({fmt_cb})", ve_cb)

        # 6. Xóa hang_ghe
        cursor.execute("DELETE FROM hang_ghe WHERE chuyen_bay_id = %s", (cb_id,))

        # 7. Xóa theo_doi_chuyen_bay
        cursor.execute("DELETE FROM theo_doi_chuyen_bay WHERE chuyen_bay_id = %s", (cb_id,))

        # 8. Xóa danh_gia
        cursor.execute("DELETE FROM danh_gia WHERE chuyen_bay_id = %s", (cb_id,))

        # 9. Set NULL thong_bao
        cursor.execute("UPDATE thong_bao SET chuyen_bay_id = NULL WHERE chuyen_bay_id = %s", (cb_id,))

        # 10. Xóa chuyến bay
        cursor.execute("DELETE FROM chuyen_bay WHERE id = %s", (cb_id,))

        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# Thông báo delay
@admin_bp.route('/thong-bao-delay/<int:cb_id>', methods=['POST'])
def thong_bao_delay(cb_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT cb.so_hieu_cb, cb.gio_cat_canh,
               sb_di.ma_iata AS tu, sb_den.ma_iata AS den
        FROM chuyen_bay cb
        JOIN tuyen_duong td ON cb.tuyen_duong_id = td.id
        JOIN san_bay sb_di  ON td.san_bay_di_id  = sb_di.id
        JOIN san_bay sb_den ON td.san_bay_den_id = sb_den.id
        WHERE cb.id = %s
    """, (cb_id,))
    cb = cursor.fetchone()
    if not cb:
        return jsonify({'error': 'Không tìm thấy chuyến bay'}), 404
    cursor.execute("""
        SELECT DISTINCT kh.ho_ten, kh.email, kh.so_dien_thoai
        FROM ve v
        JOIN dat_ve dv ON v.dat_ve_id = dv.id
        JOIN khach_hang kh ON dv.khach_hang_id = kh.id
        WHERE v.chuyen_bay_id = %s AND v.trang_thai NOT IN ('da_huy')
    """, (cb_id,))
    khach_hang_list = cursor.fetchall()
    cursor.execute("UPDATE chuyen_bay SET trang_thai = 'tre_gio' WHERE id = %s", (cb_id,))
    for kh in khach_hang_list:
        cursor.execute("SELECT id FROM khach_hang WHERE email = %s", (kh['email'],))
        kh_row = cursor.fetchone()
        if kh_row:
            cursor.execute("""
                INSERT INTO thong_bao (khach_hang_id, chuyen_bay_id, tieu_de, noi_dung, loai)
                VALUES (%s, %s, %s, %s, 'delay')
            """, (
                kh_row['id'], cb_id,
                f"Chuyến bay {cb['so_hieu_cb']} trễ giờ",
                f"Chuyến bay {cb['so_hieu_cb']} ({cb['tu']}→{cb['den']}) bị trễ giờ."
            ))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'success': True, 'chuyen_bay': cb,
                    'so_khach': len(khach_hang_list), 'khach_hang': khach_hang_list})

# Lấy khách hàng theo chuyến bay
@admin_bp.route('/khach-hang-chuyen-bay/<int:cb_id>', methods=['GET'])
def khach_hang_chuyen_bay(cb_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT DISTINCT kh.ho_ten, kh.email, kh.so_dien_thoai
        FROM ve v
        JOIN dat_ve dv ON v.dat_ve_id = dv.id
        JOIN khach_hang kh ON dv.khach_hang_id = kh.id
        WHERE v.chuyen_bay_id = %s AND v.trang_thai NOT IN ('da_huy')
    """, (cb_id,))
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(data)

# Danh sách hãng hàng không
@admin_bp.route('/hang-hang-khong', methods=['GET'])
def ds_hang_hang_khong():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, ma_hang, ten_hang FROM hang_hang_khong")
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(data)

# Danh sách sân bay
@admin_bp.route('/san-bay', methods=['GET'])
def ds_san_bay():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT ma_iata, ten_san_bay, thanh_pho, quoc_gia FROM san_bay ORDER BY quoc_gia, thanh_pho")
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(data)

# Danh sách thông báo
@admin_bp.route('/thong-bao', methods=['GET'])
def ds_thong_bao():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT tb.*, kh.ho_ten AS ten_khach
        FROM thong_bao tb
        LEFT JOIN khach_hang kh ON tb.khach_hang_id = kh.id
        ORDER BY tb.ngay_tao DESC LIMIT 50
    """)
    data = cursor.fetchall()
    for d in data:
        d['ngay_tao'] = str(d['ngay_tao'])
    cursor.close()
    conn.close()
    return jsonify(data)

# Lấy danh sách vé theo đơn
@admin_bp.route('/ve-theo-don/<int:dat_ve_id>', methods=['GET'])
def ve_theo_don(dat_ve_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT v.*, hg.ten_hang AS hang_ghe_ten,
               cb.so_hieu_cb,
               sb_di.ma_iata AS tu, sb_den.ma_iata AS den
        FROM ve v
        JOIN hang_ghe hg    ON v.hang_ghe_id    = hg.id
        JOIN chuyen_bay cb  ON v.chuyen_bay_id  = cb.id
        JOIN tuyen_duong td ON cb.tuyen_duong_id = td.id
        JOIN san_bay sb_di  ON td.san_bay_di_id  = sb_di.id
        JOIN san_bay sb_den ON td.san_bay_den_id = sb_den.id
        WHERE v.dat_ve_id = %s
    """, (dat_ve_id,))
    data = cursor.fetchall()
    for d in data:
        d['ngay_sinh'] = str(d['ngay_sinh']) if d['ngay_sinh'] else None
    cursor.close()
    conn.close()
    return jsonify(data)

# Sửa vé
@admin_bp.route('/ve/sua/<int:ve_id>', methods=['PUT'])
def sua_ve(ve_id):
    data = request.json
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE ve SET
                ho_ten      = %s,
                ngay_sinh   = %s,
                gioi_tinh   = %s,
                so_ho_chieu = %s,
                so_ghe      = %s,
                gia_ve      = %s,
                trang_thai  = %s
            WHERE id = %s
        """, (
            data.get('ho_ten'), data.get('ngay_sinh') or None,
            data.get('gioi_tinh'), data.get('so_ho_chieu'),
            data.get('so_ghe'), data.get('gia_ve'),
            data.get('trang_thai'), ve_id
        ))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


# Xóa vé
@admin_bp.route('/ve/xoa/<int:ve_id>', methods=['DELETE'])
def xoa_ve(ve_id):
    conn = get_connection()
    if not conn:
        return jsonify({'error': 'Không kết nối được database'}), 500
    cursor = conn.cursor(dictionary=True)
    try:
        # Kiểm tra vé tồn tại
        cursor.execute("SELECT id, dat_ve_id FROM ve WHERE id = %s", (ve_id,))
        ve = cursor.fetchone()
        if not ve:
            return jsonify({'error': 'Không tìm thấy vé'}), 404

        # Xóa dịch vụ bổ sung của vé
        cursor.execute("DELETE FROM dich_vu_bo_sung WHERE ve_id = %s", (ve_id,))

        # Xóa vé
        cursor.execute("DELETE FROM ve WHERE id = %s", (ve_id,))

        # Cập nhật tổng tiền đơn đặt vé
        cursor.execute("""
            UPDATE dat_ve SET tong_tien = (
                SELECT COALESCE(SUM(gia_ve), 0) FROM ve WHERE dat_ve_id = %s
            ) WHERE id = %s
        """, (ve['dat_ve_id'], ve['dat_ve_id']))

        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


# Đổi chuyến bay cho vé
@admin_bp.route('/ve/doi-chuyen/<int:ve_id>', methods=['PUT'])
def doi_chuyen_bay(ve_id):
    data          = request.json
    cb_moi_id     = data.get('chuyen_bay_id')
    hang_ghe_moi  = data.get('hang_ghe_id')

    if not cb_moi_id or not hang_ghe_moi:
        return jsonify({'error': 'Thiếu thông tin chuyến bay mới'}), 400

    conn = get_connection()
    if not conn:
        return jsonify({'error': 'Không kết nối được database'}), 500
    cursor = conn.cursor(dictionary=True)
    try:
        # Kiểm tra vé tồn tại
        cursor.execute("SELECT * FROM ve WHERE id = %s", (ve_id,))
        ve = cursor.fetchone()
        if not ve:
            return jsonify({'error': 'Không tìm thấy vé'}), 404

        # Kiểm tra chuyến bay mới còn ghế không
        cursor.execute("""
            SELECT so_ghe_con_lai, gia_nguoi_lon FROM hang_ghe
            WHERE id = %s
        """, (hang_ghe_moi,))
        hang_ghe = cursor.fetchone()
        if not hang_ghe:
            return jsonify({'error': 'Không tìm thấy hạng ghế'}), 404
        if hang_ghe['so_ghe_con_lai'] <= 0:
            return jsonify({'error': 'Chuyến bay này đã hết ghế!'}), 400

        # Hoàn ghế cho chuyến cũ
        cursor.execute("""
            UPDATE hang_ghe SET so_ghe_con_lai = so_ghe_con_lai + 1
            WHERE id = %s
        """, (ve['hang_ghe_id'],))

        # Trừ ghế ở chuyến mới
        cursor.execute("""
            UPDATE hang_ghe SET so_ghe_con_lai = so_ghe_con_lai - 1
            WHERE id = %s
        """, (hang_ghe_moi,))

        # Cập nhật vé
        cursor.execute("""
            UPDATE ve SET
                chuyen_bay_id = %s,
                hang_ghe_id   = %s,
                gia_ve        = %s,
                trang_thai    = 'da_xac_nhan'
            WHERE id = %s
        """, (cb_moi_id, hang_ghe_moi, hang_ghe['gia_nguoi_lon'], ve_id))

        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


# Xóa đơn đặt vé
@admin_bp.route('/don-dat-ve/xoa/<int:dat_ve_id>', methods=['DELETE'])
def xoa_don_dat_ve(dat_ve_id):
    conn = get_connection()
    if not conn:
        return jsonify({'error': 'Không kết nối được database'}), 500
    cursor = conn.cursor(dictionary=True)
    try:
        # Lấy danh sách vé
        cursor.execute("SELECT id FROM ve WHERE dat_ve_id = %s", (dat_ve_id,))
        ve_ids = [v['id'] for v in cursor.fetchall()]

        if ve_ids:
            fmt = ','.join(['%s'] * len(ve_ids))
            # Xóa dịch vụ bổ sung
            cursor.execute(f"DELETE FROM dich_vu_bo_sung WHERE ve_id IN ({fmt})", ve_ids)
            # Hoàn ghế
            for ve_id in ve_ids:
                cursor.execute("""
                    UPDATE hang_ghe hg
                    JOIN ve v ON v.hang_ghe_id = hg.id
                    SET hg.so_ghe_con_lai = hg.so_ghe_con_lai + 1
                    WHERE v.id = %s
                """, (ve_id,))
            # Xóa vé
            cursor.execute(f"DELETE FROM ve WHERE id IN ({fmt})", ve_ids)

        # Xóa đánh giá liên quan
        cursor.execute("DELETE FROM danh_gia WHERE dat_ve_id = %s", (dat_ve_id,))
        # Xóa thanh toán
        cursor.execute("DELETE FROM thanh_toan WHERE dat_ve_id = %s", (dat_ve_id,))
        # Xóa hỗ trợ liên quan
        cursor.execute("UPDATE ho_tro SET dat_ve_id = NULL WHERE dat_ve_id = %s", (dat_ve_id,))
        # Xóa đơn
        cursor.execute("DELETE FROM dat_ve WHERE id = %s", (dat_ve_id,))

        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()