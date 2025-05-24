frappe.ui.form.on('Vehicle', {
    refresh: function(frm) {
        // Hanya tampilkan tombol jika dokumen sudah disimpan
        if (!frm.is_new()) {
            frm.add_custom_button(__('Lihat Perubahan Terakhir'), function() {
                // Panggil API untuk mendapatkan log perubahan terakhir
                frappe.call({
                    method: 'car_workshop.car_workshop.api.get_latest_vehicle_log',
                    args: {
                        vehicle: frm.doc.name
                    },
                    callback: function(response) {
                        if (response.message) {
                            // Jika log ditemukan
                            const log = response.message;
                            
                            // Format tanggal ke format lokal
                            const formattedDate = frappe.datetime.str_to_user(
                                log.change_date
                            );
                            
                            // Siapkan pesan yang akan ditampilkan
                            let message = `
                                <div style="max-width: 500px;">
                                    <div class="font-weight-bold mb-2 text-primary">
                                        ${log.change_type || 'Perubahan'}
                                    </div>
                                    
                                    <div class="row mb-2">
                                        <div class="col-4 font-weight-bold">Field</div>
                                        <div class="col-8">${frappe.meta.get_label('Vehicle', log.fieldname) || log.fieldname}</div>
                                    </div>`;
                            
                            // Tambahkan old value dan new value jika tersedia
                            if (log.old_value || log.new_value) {
                                message += `
                                    <div class="row mb-2">
                                        <div class="col-4 font-weight-bold">Nilai Lama</div>
                                        <div class="col-8">${log.old_value || '-'}</div>
                                    </div>
                                    <div class="row mb-2">
                                        <div class="col-4 font-weight-bold">Nilai Baru</div>
                                        <div class="col-8">${log.new_value || '-'}</div>
                                    </div>`;
                            }
                            
                            // Tambahkan informasi tanggal dan user
                            message += `
                                <div class="row mb-2">
                                    <div class="col-4 font-weight-bold">Tanggal</div>
                                    <div class="col-8">${formattedDate}</div>
                                </div>
                                <div class="row mb-2">
                                    <div class="col-4 font-weight-bold">Oleh</div>
                                    <div class="col-8">${log.updated_by}</div>
                                </div>`;
                            
                            // Tambahkan remarks jika tersedia
                            if (log.remarks) {
                                message += `
                                    <div class="row mb-2">
                                        <div class="col-4 font-weight-bold">Catatan</div>
                                        <div class="col-8">${log.remarks}</div>
                                    </div>`;
                            }
                            
                            message += `</div>`;
                            
                            // Tampilkan pesan
                            frappe.msgprint({
                                title: __('Perubahan Terakhir'),
                                indicator: 'blue',
                                message: message
                            });
                        } else {
                            // Jika tidak ada log yang ditemukan
                            frappe.msgprint({
                                title: __('Info'),
                                indicator: 'gray',
                                message: __('Belum ada perubahan tercatat.')
                            });
                        }
                    }
                });
            }, __('Actions'));
            
            // Tambahkan tombol untuk melihat semua perubahan
            frm.add_custom_button(__('Lihat Semua Perubahan'), function() {
                frappe.route_options = {
                    vehicle: frm.doc.name
                };
                frappe.set_route('List', 'Vehicle Change Log');
            }, __('Actions'));
        }
    }
});