;(function (define, undefined) {
    'use strict';
    define([
        'gettext', 'jquery', 'underscore', 'backbone'
    ], function (gettext, $, _, Backbone) {

        var LearnerProfileReadonlyView = Backbone.View.extend({

            initialize: function (options) {
                this.template = _.template($('#learner_profile_readonly-tpl').text());
            },

            render: function () {
                this.$el.html(this.template({
                    profileVisibility: this.getProfileVisibility(),
                    profileImageUrl: "http://www.teachthought.com/wp-content/uploads/2012/07/edX-120x120.jpg",
                    username: this.model.get('username'),
                    country: this.model.get('country'),
                    language: this.model.get('language'),
                    bio: this.model.get('bio')
                }));
                return this;
            },

            getProfileVisibility: function () {
                if (this.options.info.own_profile) {
                    return this.options.preferencesModel.get('account_privacy');
                } else {
                    return this.model.get('profilePrivacy');
                }
            }
        });

        return LearnerProfileReadonlyView;
    })
}).call(this, define || RequireJS.define);