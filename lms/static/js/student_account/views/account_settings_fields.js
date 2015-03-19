;(function (define, undefined) {
    'use strict';
    define([
        'gettext', 'jquery', 'underscore', 'backbone', 'js/vendor/backbone-super',
    ], function (gettext, $, _, Backbone) {

        var messageRevertDelay = 4000;
        var AccountSettingsFieldViews = {};

        AccountSettingsFieldViews.FieldView = Backbone.View.extend({

            className: function () {
                return "account-settings-field " + "account-settings-field-" + this.options.valueAttribute;
            },

            tagName: 'div',

            indicators: {
                'error': '<i class="fa fa-exclamation-triangle message-error"></i>',
                'invalidInput': '<i class="fa fa-exclamation-triangle message-invalid-input"></i>',
                'inProgress': '<i class="fa fa-spinner message-in-progress"></i>',
                'success': '<i class="fa fa-check message-success"></i>',
            },

            messages: {
                'error': gettext('An error occurred, please try again.'),
                'invalidInput': '',
                'inProgress': gettext('Saving...'),
                'success': gettext('Successfully changed.'),
            },

            initialize: function (options) {

                this.template = _.template($(this.templateSelector).text());

                this.helpMessage = this.options.helpMessage || '';
                this.showMessages = _.isUndefined(this.options.showMessages) ? true : this.options.showMessages;

                _.bindAll(this, 'modelValue', 'saveAttributes', 'getMessage',
                    'message', 'showHelpMessage', 'showInProgressMessage', 'showSuccessMessage', 'showErrorMessage');
            },

            modelValue: function () {
                return this.model.get(this.options.valueAttribute);
            },

            saveAttributes: function (attributes, options) {
                var view = this;
                var defaultOptions = {
                    contentType: 'application/merge-patch+json',
                    patch: true,
                    wait: true,
                    success: function (model, response, options) {
                        view.showSuccessMessage()
                    },
                    error: function (model, xhr, options) {
                        view.showErrorMessage(xhr)
                    },
                };
                this.showInProgressMessage();
                this.model.save(attributes, _.extend(defaultOptions, options));
            },

            message: function (message) {
                return this.$('.account-settings-field-message').html(message);
            },

            getMessage: function(message_status) {
                if ((message_status + 'Message') in this) {
                    return this[message_status + 'Message'].call(this);
                } else if (this.showMessages) {
                    return this.indicators[message_status] + this.messages[message_status];
                }
                return this.indicators[message_status];
            },

            showHelpMessage: function () {
                this.message(this.helpMessage);
            },

            showInProgressMessage: function () {
                this.message(this.getMessage('inProgress'));
            },

            showSuccessMessage: function () {
                var successMessage = this.getMessage('success');
                this.message(successMessage);

                if (this.options.refreshPageOnSave) {
                    document.location.reload();
                }

                var view = this;

                var context = Date.now()
                this.lastSuccessMessageContext = context;

                setTimeout(function () {
                    if ((context === view.lastSuccessMessageContext) && (view.message().html() == successMessage)) {
                        view.showHelpMessage();
                    }
                }, messageRevertDelay);
            },

            showErrorMessage: function (xhr) {
                if (xhr.status === 400) {
                    try {
                        var errors = JSON.parse(xhr.responseText);
                        var message = this.indicators['invalidInput'] + errors['field_errors'][this.options.valueAttribute]['user_message'];
                        this.message(message);
                    } catch (error) {
                        this.message(this.getMessage('error'));
                    }
                } else {
                    this.message(this.getMessage('error'));
                }
            },
        });

        AccountSettingsFieldViews.ReadonlyFieldView = AccountSettingsFieldViews.FieldView.extend({

            templateSelector: '#field_readonly-tpl',

            initialize: function (options) {
                this._super(options);
                _.bindAll(this, 'render', 'updateValueInField');
                this.listenTo(this.model, "change:" + this.options.valueAttribute, this.updateValueInField);
            },

            render: function () {
                this.$el.html(this.template({
                    title: this.options.title,
                    value: this.modelValue(),
                    message: this.helpMessage,
                }));
                return this;
            },

            updateValueInField: function () {
                this.$('.account-settings-field-value').html(this.modelValue());
            },
        });

        AccountSettingsFieldViews.TextFieldView = AccountSettingsFieldViews.FieldView.extend({

            templateSelector: '#field_text-tpl',

            events: {
                'change input': 'saveValue',
            },

            initialize: function (options) {
                this._super(options);
                _.bindAll(this, 'render', 'fieldValue', 'updateValueInField', 'saveValue');
                this.listenTo(this.model, "change:" + this.options.valueAttribute, this.updateValueInField);
            },

            render: function () {
                this.$el.html(this.template({
                    title: this.options.title,
                    value: this.modelValue(),
                    message: this.helpMessage,
                }));
                return this;
            },

            fieldValue: function () {
                return this.$('.account-settings-field-value input').val();
            },

            updateValueInField: function () {
                this.$('.account-settings-field-value input').val(this.modelValue() || '');
            },

            saveValue: function (event) {
                var attributes = {};
                attributes[this.options.valueAttribute] = this.fieldValue();
                this.saveAttributes(attributes);

            },
        });

        AccountSettingsFieldViews.EmailFieldView = AccountSettingsFieldViews.TextFieldView.extend({

            successMessage: function() {
                return this.indicators['success'] + interpolate_text(
                    gettext('Complete you email change by clicking the confirmation link emailed to {new_email_address}.'),
                    {'new_email_address': this.fieldValue()}
                );
            },
        });

        AccountSettingsFieldViews.DropdownFieldView = AccountSettingsFieldViews.FieldView.extend({

            templateSelector: '#field_dropdown-tpl',

            events: {
                'change select': 'saveValue'
            },

            initialize: function (options) {
                this._super(options);
                _.bindAll(this, 'render', 'fieldValue', 'updateValueInField', 'saveValue');
                this.listenTo(this.model, "change:" + this.options.valueAttribute, this.updateValueInField);
            },

            render: function () {
                this.$el.html(this.template({
                    title: this.options.title,
                    required: this.options.required,
                    selectOptions: this.options.options,
                    message: this.helpMessage,
                    showElement: _.isUndefined(this.options.showElement) ? true : this.options.showElement
                }));
                this.updateValueInField();
                return this;
            },

            fieldValue: function () {
                return this.$('.account-settings-field-value select').val();
            },

            updateValueInField: function () {
                this.$('.account-settings-field-value select').val(this.modelValue() || "");
            },

            saveValue: function () {
                var attributes = {};
                attributes[this.options.valueAttribute] = this.fieldValue();
                this.saveAttributes(attributes);

            }
        });

        AccountSettingsFieldViews.TextareaFieldView = AccountSettingsFieldViews.FieldView.extend({

            templateSelector: '#field_textarea-tpl',

            events: {
                'focusout textarea': 'finishEditing',
                'click .account-settings-field-wrapper': 'editValue',
                'click .account-settings-field-placeholder': 'editValue'
            },
            errorMessage: '<i class="fa fa-exclamation-triangle message-error"></i>',
            invalidInputMessagePrefix: '<i class="fa fa-exclamation-triangle message-invalid-input"></i>',
            inProgressMessage: '<i class="fa fa-spinner message-in-progress"></i>',
            successMessagePrefix: '<i class="fa fa-check message-success"></i>',


            initialize: function (options) {
                this._super(options);
                _.bindAll(this, 'render', 'fieldValue', 'updateValueInField', 'finishEditing', 'editValue');
                if (this.modelValue() ) {
                    this.state = 'display'
                } else {
                    this.state = 'placeholder'
                }
                this.helpMessage = '<i class="icon fa fa-pencil"></i>';
                this.listenTo(this.model, "change:" + this.options.valueAttribute, this.updateValueInField);
            },

            render: function () {
                this.$el.html(this.template({
                    title: this.options.title,
                    value: this.currentValue(),
                    state: this.state,
                    message: this.helpMessage
                }));
                return this;
            },

            fieldValue: function () {
                return this.$('.account-settings-field-edit').val();
            },

            updateValueInField: function () {
                this.$('.account-settings-field-value textarea').val(this.modelValue() || "");
            },

            saveValue: function () {
                var attributes = {};
                attributes[this.options.valueAttribute] = this.fieldValue();
                this.saveAttributes(attributes);
            },

            currentValue: function () {
                if (_.isNull(this.newValue) || _.isUndefined(this.newValue)) {
                  return _.isNull(this.modelValue()) ? '' : this.modelValue();
                } else {
                  return this.newValue;
                }
            },

            finishEditing: function(event) {

                this.newValue = this.fieldValue();
                if (this.newValue) {
                    this.state = 'display';
                } else {
                    this.state = 'placeholder';
                }
                this.render();

                if (this.newValue !== this.modelValue()) {
                    this.saveValue();
                }
            },

            editValue: function (event) {
                if (this.state !== 'edit') {
                    this.state = 'edit';
                    this.render();
                    this.$('.account-settings-field-edit').focus();
                }
            },

            successMessage: function() {
                return this.successMessagePrefix;
            }
        });

        AccountSettingsFieldViews.LinkFieldView = AccountSettingsFieldViews.FieldView.extend({

            templateSelector: '#field_link-tpl',

            events: {
                'click a': 'linkClicked',
            },

            initialize: function (options) {
                this._super(options);
                _.bindAll(this, 'render', 'linkClicked');
            },

            render: function () {
                this.$el.html(this.template({
                    title: this.options.title,
                    linkTitle: this.options.linkTitle,
                    linkHref: this.options.linkHref,
                    message: this.helpMessage,
                }));
                return this;
            },

            linkClicked: function () {
                event.preventDefault();
            },
        });

        AccountSettingsFieldViews.PasswordFieldView = AccountSettingsFieldViews.LinkFieldView.extend({

            initialize: function (options) {
                this._super(options);
                _.bindAll(this, 'resetPassword');
            },

            linkClicked: function (event) {
                event.preventDefault();
                this.resetPassword(event)
            },

            resetPassword: function (event) {
                var data = {};
                data[this.options.emailAttribute] = this.model.get(this.options.emailAttribute);

                var view = this;
                $.ajax({
                    type: 'POST',
                    url: view.options.linkHref,
                    data: data,
                    success: function (data, status, xhr) {
                        view.showSuccessMessage()
                    },
                    error: function (xhr, status, error) {
                        view.showErrorMessage(xhr);
                    }
                });
            },

            successMessage: function() {
                return this.indicators['success'] + interpolate_text(
                    gettext('Complete you password reset using the confirmation link emailed to {email_address}.'),
                    {'email_address': this.model.get(this.options.emailAttribute)}
                );
            },
        });

        return AccountSettingsFieldViews;
    })
}).call(this, define || RequireJS.define);
