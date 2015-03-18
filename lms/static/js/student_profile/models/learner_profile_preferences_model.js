;(function (define, undefined) {
    'use strict';
    define([
        'gettext', 'underscore', 'backbone',
    ], function (gettext, _, Backbone) {

        var LearnerProfilePreferencesModel = Backbone.Model.extend({
            idAttribute: 'account_privacy',
            defaults: {
                account_privacy: 'private'
            }
        });

        return LearnerProfilePreferencesModel;
    })
}).call(this, define || RequireJS.define);
