frappe.ui.form.on("Customer Vehicle", {
    refresh: function(frm) {
        // Tampilkan tombol jika dokumen sudah disimpan
        if (!frm.is_new()) {
            frm.add_custom_button(__('Lihat Perubahan Terakhir'), function() {
                frappe.call({
                    method: 'car_workshop.car_workshop.api.get_latest_vehicle_log',
                    args: {
                        customer_vehicle: frm.doc.name
                    },
                    callback: function(response) {
                        if (response.message) {
                            const log = response.message;
                            const formattedDate = frappe.datetime.str_to_user(log.change_date);
                            const escape = frappe.utils.escape_html;

                            const changeType = escape(log.change_type || 'Perubahan');
                            const fieldLabel = escape(frappe.meta.get_label('Customer Vehicle', log.fieldname) || log.fieldname);
                            const oldValue = escape(log.old_value || '-');
                            const newValue = escape(log.new_value || '-');
                            const safeDate = escape(formattedDate);
                            const updatedBy = escape(log.updated_by || '');
                            const remarks = log.remarks ? escape(log.remarks) : '';

                            let message = `
                                <div style="max-width: 500px;">
                                    <div class="font-weight-bold mb-2 text-primary">
                                        ${changeType}
                                    </div>
                                    <div class="row mb-2">
                                        <div class="col-4 font-weight-bold">Field</div>
                                        <div class="col-8">${fieldLabel}</div>
                                    </div>`;

                            if (log.old_value || log.new_value) {
                                message += `
                                    <div class="row mb-2">
                                        <div class="col-4 font-weight-bold">Nilai Lama</div>
                                        <div class="col-8">${oldValue}</div>
                                    </div>
                                    <div class="row mb-2">
                                        <div class="col-4 font-weight-bold">Nilai Baru</div>
                                        <div class="col-8">${newValue}</div>
                                    </div>`;
                            }

                            message += `
                                <div class="row mb-2">
                                    <div class="col-4 font-weight-bold">Tanggal</div>
                                    <div class="col-8">${safeDate}</div>
                                </div>
                                <div class="row mb-2">
                                    <div class="col-4 font-weight-bold">Oleh</div>
                                    <div class="col-8">${updatedBy}</div>
                                </div>`;

                            if (log.remarks) {
                                message += `
                                    <div class="row mb-2">
                                        <div class="col-4 font-weight-bold">Catatan</div>
                                        <div class="col-8">${remarks}</div>
                                    </div>`;
                            }

                            message += `</div>`;

                            frappe.msgprint({
                                title: __('Perubahan Terakhir'),
                                indicator: 'blue',
                                message: message
                            });
                        } else {
                            frappe.msgprint({
                                title: __('Info'),
                                indicator: 'gray',
                                message: __('Belum ada perubahan tercatat.')
                            });
                        }
                    }
                });
            }, __('Actions'));

            frm.add_custom_button(__('Lihat Semua Perubahan'), function() {
                frappe.route_options = {
                    customer_vehicle: frm.doc.name
                };
                frappe.set_route('List', 'Vehicle Change Log');
            }, __('Actions'));
        }
    },

    brand: function(frm) {
        frm.set_value("model", "");
        frm.set_query("model", function() {
            return {
                filters: {
                    brand: frm.doc.brand
                }
            };
        });
    },

    onload: function(frm) {
        if (frm.doc.brand) {
            frm.set_query("model", function() {
                return {
                    filters: {
                        brand: frm.doc.brand
                    }
                };
            });
        }
    }
});
