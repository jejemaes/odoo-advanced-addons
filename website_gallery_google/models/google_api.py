# -*- coding: utf-8 -*-

import logging

import requests
from werkzeug import urls

from odoo import api, fields, models, registry, _
from odoo.exceptions import UserError


from odoo.addons.google.models.google_api import GoogleException

_logger = logging.getLogger(__name__)

GOOGLE_PHOTOS_BASE_ENDPOINT = 'https://photoslibrary.googleapis.com/v1/'


class GoogleAPI(models.AbstractModel):
    _inherit = 'google.api'

    def _api_scopes_map(self):
        """ List of scope for google photos API : https://developers.google.com/photos/library/guides/authentication-authorization """
        result = super(GoogleAPI, self)._api_scopes_map()
        result['website_gallery'] = [
            'https://www.googleapis.com/auth/photoslibrary',
            'https://www.googleapis.com/auth/photoslibrary.readonly',
            'https://www.googleapis.com/auth/photoslibrary.readonly.appcreateddata',
        ]
        return result

    # ---------------------------------------------------------
    # Google Photos API
    # ---------------------------------------------------------

    def _photos_fetch_albums(self, page_size=50, next_page_token=False):
        """
            :param date_start: start date range to search albums
            :param date_stop: end date range to search albums

            Returns data by Google API are like
            {
              "albums": [
                {
                  "id": "AEDhYeMd6LCIE_DKGDsH5uPscBuh9rZwLEvolUX3JrG5W53dOuCC56wSGRlhmkjzgAxaomkM",
                  "title": "2018 - Ducasse: Mothercover et Mambassa BB (Vendredi Soir) ",
                  "productUrl": "https://photos.google.com/lr/album/AEDhYeMd6LCIE_DKGDsuPscBuh9...",
                  "mediaItemsCount": "87",
                  "coverPhotoBaseUrl": "https://lh3.googleusercontent.com/lr/AGWb-e4Qb4zH4kL87s...",
                  "coverPhotoMediaItemId": "AEDhYeOUORQ_nvZPvLmCaXGAF7bFo6X7ENJFLcsK9Lb5Vu0bzclJ..."
                },
                ...
              ],
              "nextPageToken": "CkAKPnR5cGUuZ29vZ2xlYXBpcy5jb20vZ29vZ2xlLnBob3Rvcy5saWJyYXJ5LuV0..."
            }
        """
        scopes = self.env['google.api']._api_get_scopes('website_gallery')
        access_token = self.env['res.users'].browse(self.env.user.id)._google_get_valid_token(scopes)[self.env.user.id]
        endpoint = '%s%s' % (GOOGLE_PHOTOS_BASE_ENDPOINT, 'albums')
        params = {
            'pageSize': max(page_size or 50, 50),
        }
        # include next page token
        if isinstance(next_page_token, str):
            params['nextPageToken'] = next_page_token

        (status, response) = self._api_do_request(endpoint, access_token, method='GET', params=params)
        if status != 200:
            return {}
        return response['albums'], response.get('nextPageToken')

    def _photos_fetch_media_items(self, album_id, next_page_token=False):
        """
            :param album_id: google identifier of the album

            The response from google looks like
            {
              "mediaItems": [
                {
                  "id": "AEDhYeO7MtyMH2OPduoDU-IAs2NeOzwMp4FQ0iwUZbedVBi00R1bVQbeWzuuDdwR77ZLmxR3P...",
                  "productUrl": "https://photos.google.com/lr/album/AEDhYeMeKkFP...uVT7Eo2IdBd2YN2Ks0h5r/photo/AEDhYeO7MtyMH2OPduoDU",
                  "baseUrl": "https://lh3.googleusercontent.com/lr/AGWb-e7...XNeta-0lZeawLr1Bkv2FKm2BcmYTmkGL5IlZGprY6fHdYrf0sLEOYP-...",
                  "mimeType": "image/jpeg",
                  "mediaMetadata": {
                    "creationTime": "2019-12-21T17:58:59Z",
                    "width": "4608",
                    "height": "3072",
                    "photo": {
                      "cameraMake": "NIKON CORPORATION",
                      "cameraModel": "NIKON D3100",
                      "focalLength": 18,
                      "apertureFNumber": 3.5,
                      "isoEquivalent": 1600
                    }
                  },
                  "filename": "DSC_0490.JPG"
                },
                ...
              ],
              "nextPageToken": "CpYBCkR0eXBlLmdvb2dsZWFwaXMuY29tL2dvb2dsZS5waG90b3MubGli2MS5TZWF..."
            }
        """
        scopes = self.env['google.api']._api_get_scopes('website_gallery')
        access_token = self.env['res.users'].browse(self.env.user.id)._google_get_valid_token(scopes)[self.env.user.id]
        endpoint = '%s%s' % (GOOGLE_PHOTOS_BASE_ENDPOINT, 'mediaItems:search')
        params = {
            'albumId': album_id
        }
         # include next page token
        if isinstance(next_page_token, str):
            params['pageToken'] = next_page_token

        (status, response) = self._api_do_request(endpoint, access_token, method='POST', params=params)
        if status != 200:
            return {}
        return response['mediaItems'], response.get('nextPageToken')

    def _photos_fetch_all_media_items(self, album_id):
        result = []
        next_page_token = True
        while next_page_token:
            items, next_page_token = self._photos_fetch_media_items(album_id, next_page_token=next_page_token)
            result += items
        return result

    def _photos_create_gallery_image(self, gallery_id, media_items):
        values_list = []
        for media_item in media_items:
            values_list.append(self._photos_prepare_gallery_image_values(gallery_id, media_item))
        return self.env['website.gallery.image'].create(values_list)

    def _photos_prepare_gallery_image_values(self, gallery_id, media_item):
        """ Convert the mediaItem from Google into values to create the Odoo model of
            website.gallery.image
        """
        return {
            'gallery_id': gallery_id,
            'name': media_item['filename'],
            'datas_fname': media_item['filename'],
            'mimetype': media_item['mimeType'],
            'type': 'url',
            'url': media_item['baseUrl'],
        }
