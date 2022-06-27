odoo.define('ezp_cash_collection.building_room_summary', function (require) {
    'use strict';

    var core = require('web.core');
    var registry = require('web.field_registry');
    var basicFields = require('web.basic_fields');
    var FieldText = basicFields.FieldText;
    var QWeb = core.qweb;
    var FormView = require('web.FormView');
    var py = window.py;

    var MyWidget = FieldText.extend({
        events: _.extend({}, FieldText.prototype.events, {
            'change': '_onFieldChanged',
        }),
        init: function() {
        debugger;
            this._super.apply(this, arguments);
            if (this.mode === 'edit') {
                this.tagName = 'span';
            }
            this.set({
                date_to: false,
                date_from: false,
                summary_header: false,
                summary_footer: false,
                room_summary: false,
            });
            this.set({
                "summary_header": py.eval(this.recordData.summary_header)
            });
            this.set({
                "room_summary": py.eval(this.recordData.room_summary)
            });
            this.set({
                "summary_footer": py.eval(this.recordData.summary_footer)
            });
        },
        start: function () {
            var self = this;
            if (self.setting) {
                return;
            }
            if (!this.get("summary_header") || !this.get("room_summary")) {
                return;
            }
            if (!this.get("summary_footer") || !this.get("summary_footer")) {
                return;
            }
            this.renderElement();
            this.view_loading();
        },
        initialize_field: function () {
            FormView.ReinitializeWidgetMixin.initialize_field.call(this);
            var self = this;
            self.on("change:summary_header", self, self.start);
            self.on("change:room_summary", self, self.start);
            self.on("change:summary_footer", self, self.start);
        },
        view_loading: function (r) {
            debugger;
            return this.load_form(r);
        },

        load_form: function () {
        debugger;
            var self = this;
//            this.$el.find(".table_free").bind("click", function () {
             this.$el.find(".table_vaccant").bind("click", function () {
                self.do_action({
                    type: 'ir.actions.act_window',
//                    res_model: "quick.building.reservation",
                    res_model: "crm.lead",
                    views: [
                        [false, 'form']
                    ],
                    target: 'new',
//                    context: {
//                        "room_id": $(this).attr("data"),
//                        'date': $(this).attr("date"),
////                        'default_adults': 1
//                    },
                });
            });
             this.$el.find(".table_liked").bind("click", function () {
             debugger;
             var rpc = require('web.rpc')
             $(this)[0].id = 'test_liked'.concat($(this).context.dataset.id)
             var ele = document.getElementById ( $(this)[0].id );
             var element = parseInt(document.getElementById ( $(this)[0].id).dataset.id);
//             var element1 =$(this).context.dataset.id.split(",")[0]
//             var element2 =$(this).context.dataset.id.split(",")[1]
//             var m=parseInt(element1)
//             var n=parseInt(element2)
//             var g =[];
//             g.push(m)
//             g.push(n)
             var g =[];
             for(var i=0;i<= $(this).context.dataset.id.split(",").length;i++){
             debugger;
                 var element1 = $(this).context.dataset.id.split(",")[i]
                 var m_ids=parseInt(element1)
                 g.push(m_ids)

             }


             return rpc.query({
//                model: 'liked.customers.sum',
                model: 'liked.customers',
//                model: 'crm.lead',
                method: 'liked_customer_list',
//                args: [{'room_id':py.eval(this.value)}]
                args: [{}]


            }).then(function (result) {
              self.do_action({
                name: 'Customers',
//                res_model: 'liked.customers.sum',
                res_model: 'liked.customers',
//                res_model: 'crm.lead',
                res_id: 1,
                views: [[false, 'list']],
                type: 'ir.actions.act_window',
                domain: [['id', '=', g]],
//                domain: [['id', '=', element]],
//                domain: [['interest', '=', 'Liked']],
                view_type: 'tree',
                target: 'new',
                view_mode: 'tree',
            });

            });

            });
             this.$el.find(".table_quotation").bind("click", function () {
               debugger;
             var rpc = require('web.rpc')

//             var ele = document.getElementById ( "test_quotation" );
//             var element = parseInt(document.getElementById ( "test_quotation" ).dataset.id);
             $(this)[0].id = 'test_quotation'.concat($(this).context.dataset.id)
             var ele = document.getElementById ( $(this)[0].id );
             var element = parseInt(document.getElementById ( $(this)[0].id).dataset.id);
             var g =[];
             for(var i=0;i<= $(this).context.dataset.id.split(",").length;i++){
                 debugger;
                 var element1 = $(this).context.dataset.id.split(",")[i]
                 var m_ids=parseInt(element1)
                 g.push(m_ids)

             }



             return rpc.query({
                model: 'liked.customers',
                method: 'liked_customer_list',
                args: [{}]


            }).then(function (result) {
              self.do_action({
                name: 'Customers',
//                res_model: 'liked.customers.sum',
                res_model: 'liked.customers',
                res_id: 1,
                views: [[false, 'list']],
                type: 'ir.actions.act_window',
//                domain: [['interest', '=', 'Quotation Given']],
//               domain: [['id', '=', element]],
               domain: [['id', '=', g]],
//                domain: [['interest', '=', 'Quotation Given']],
                view_type: 'tree',
                target: 'new',
                view_mode: 'tree',
            });

            });

            });
             this.$el.find(".table_visited").bind("click", function () {
                 var rpc = require('web.rpc')
             $(this)[0].id = 'test_visited'.concat($(this).context.dataset.id)
             var ele = document.getElementById ( $(this)[0].id );
             var element = parseInt(document.getElementById ( $(this)[0].id).dataset.id);
             var g =[];
             for(var i=0;i<= $(this).context.dataset.id.split(",").length;i++){
                 debugger;
                 var element1 = $(this).context.dataset.id.split(",")[i]
                 var m_ids=parseInt(element1)
                 g.push(m_ids)

             }

             return rpc.query({
                model: 'liked.customers',
                method: 'liked_customer_list',
                args: [{}]


            }).then(function (result) {
              self.do_action({
                name: 'Customers',
                res_model: 'liked.customers',
                res_id: result,
                views: [[false, 'list']],
                type: 'ir.actions.act_window',
//                domain: [['interest', '=', 'Visited']],
                domain: [['id', '=', g]],
                view_type: 'tree',
                target: 'new',
                view_mode: 'tree',
            });

            });
            });
             this.$el.find(".table_reserved").bind("click", function () {
             debugger;
             var rpc = require('web.rpc')
//             .web.Model("your.model")
//                    .call( "delete_client_analysis_profile", [[active_id]])
//                 new instance       .then(function (result) {
//                            // do something with result
//                    });
//             var ele = document.getElementById("test_allot").dataset.id;
//             var element = parseInt(document.getElementById ( "test_allot" ).dataset.id);
//             $(this)[0].id = 'test_allot'.concat(document.getElementById ( "test_allot" ).dataset.id)
//             var ele = document.getElementById ( $(this)[0].id );
//             var element = parseInt(ele);
//             this.$el.find(".table_visited").bind("click", function () {
//                 var rpc = require('web.rpc')
             $(this)[0].id = 'test_allot'.concat($(this).context.dataset.id)
             var ele = document.getElementById ( $(this)[0].id );
             var element = parseInt(document.getElementById ( $(this)[0].id).dataset.id);


             return rpc.query({
                            model: 'flat.reg',
                            method: 'liked_customer_list',
                            args: [[element]],
             }).then(function (result) {
             debugger;
             self.do_action({
                name: 'Customers',
                res_model: 'flat.reg',
                res_id: result,
//                views: [[false, 'list']],
                type: 'ir.actions.act_window',
//                domain: [['interest', '=', 'Alloted']],
//                domain: [['id', '=', $rom]],
//                domain: [['id', '=', parseInt($(this)[0].getAttribute('data-id'))]],
//                domain: [['id', '=', parseInt(this.getAttribute('data-id'))]],
                domain: [['id', '=', element]],
                views: [
                        [false, 'form']
                    ],
                target: 'new',
//                view_mode: 'tree',

            });
            });
            });

        },
        renderElement: function () {
        debugger;
            this._super();
            this.$el.html(QWeb.render("RoomSummary", {
                widget: this
            }));
        },
        _onFieldChanged: function (event) {
        debugger;
            this._super();
            this.lastChangeEvent = event;
            this.set({
                "summary_header": py.eval(this.recordData.summary_header)
            });
            this.set({
                "room_summary": py.eval(this.recordData.room_summary)
            });
              this.set({
                "summary_footer": py.eval(this.recordData.summary_footer)
            });
            this.renderElement();
            this.view_loading();
        },
    });

    registry.add(
        'Room_Reservation', MyWidget
    );
    return MyWidget;
});
