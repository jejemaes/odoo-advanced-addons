# -*- coding: utf-8 -*-

from odoo import api, models, fields
from odoo.osv import expression


class Blog(models.Model):
    _inherit = 'blog.blog'

    @api.model
    def _default_domain_user_ids(self):
        groups = self.env['res.groups'].sudo().search([('category_id', '=', self.env.ref('website_blog_advanced.module_category_website_blog').id)])
        return [('groups_id', 'in', groups.ids)]

    user_ids = fields.Many2many('res.users', 'blog_blog_user_rel', 'blog_id', 'user_id', string="Authors", domain=lambda self: self._default_domain_user_ids())

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if self.user_has_groups('website_blog_advanced.group_website_blog_publisher_own,!website_blog_advanced.group_website_blog_publisher_global'):
            args = args or []
            rule_domain = self.env['ir.rule']._compute_domain(self._name, mode="write")
            args = expression.AND([args, rule_domain])
        return super(Blog, self).name_search(name=name, args=args, operator=operator, limit=limit)


class Post(models.Model):
    _inherit = 'blog.post'

    am_i_author = fields.Boolean(compute='_compute_am_i_author', search='_search_am_i_author')
    can_edit = fields.Boolean("Can Edit", compute='_compute_accesses')
    can_delete = fields.Boolean("Can Delete", compute='_compute_accesses')
    can_read = fields.Boolean("Can Read", compute='_compute_accesses')

    @api.depends('author_id')
    def _compute_am_i_author(self):
        for post in self:
            post.am_i_author = post.author_id == self.env.user.partner_id

    def _search_am_i_author(self, operator, value):
        negative = operator in expression.NEGATIVE_TERM_OPERATORS
        if negative  and value:
            return [('author_id', '!=', self.env.user.partner_id.id)]
        return [('author_id', '=', self.env.user.partner_id.id)]

    @api.depends('blog_id', 'author_id')
    def _compute_accesses(self):
        for post in self:
            for operation, fname in [('read', 'can_read'), ('write', 'can_edit'), ('unlink', 'can_delete')]:
                try:
                    post.check_access_rights(operation)
                    post.check_access_rule(operation)
                    post[fname] = True
                except Exception:
                    post[fname] = False
