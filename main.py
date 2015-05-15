# -*- coding: utf-8 -*-

import urllib
import urllib2
import time
import json
import os

import arcpy

timestamp = time.strftime("%Y-%m-%d-%H%M%S")

class AGOL:
    """ A class for administering an ArcGIS Online account"""

    def __init__(self, in_username, in_password, expiration=60):
        self.agol = 'https://www.arcgis.com'
        self.services = 'https://services.arcgis.com'
        self.username = in_username
        self.password = in_password
        self.expiration = expiration
        self.token = self.gen_token()

    def make_request(self, url, params):
        """ Handles all url requests """
        
        data = urllib.urlencode(params)
        req = urllib2.Request(url, data)
        return json.loads(urllib2.urlopen(req).read())
    
    def gen_token(self):
        """ Returns a token given a username and password """

        params = dict(username=self.username,
                      password=self.password,
                      expiration=self.expiration,
                      client='referer',
                      referer='https://www.arcgis.com',
                      f='json')

        url = self.agol + '/sharing/rest/generateToken'
        token = self.make_request(url, params)

        if 'error' in token:
            raise Exception(token['error']['message'], token['error']['details'])
        else:
            return token

    def get_user(self):
        """ Returns personal details of the user, such as e-mail and groups,
        which are returned only to the user or the administrator of the organization """
        
        params = dict(token=self.token['token'],
                     f='json')

        url = self.agol + '/sharing/rest/community/users/{}'.format(self.username)

        user = self.make_request(url, params)

        if 'error' in user:
            raise Exception(user['error']['message'], user['error']['details'])
        else:
            return user
        

    def get_user_content(self):
        """ Returns the content items for a particular user """

        params = dict(token=self.token['token'],
                     f='json')

        url = self.agol + '/sharing/rest/content/users/{}'.format(self.username)

        items = self.make_request(url, params)

        if 'error' in items:
            raise Exception(items['error']['message'], items['error']['details'])
        else:
            return items
        
    def export_features_single(self, org_id, name, save_loc):
        """Export a single feature layer from ArcGIS Online and saves it in a File Geodatabase"""

        service = ''.join(e for e in name if e.isalnum())
        gdb_name = 'export_' + service + '.gdb'

        service_folder = os.path.join(save_loc, name)
        os.makedirs(service_folder)

        json_folder = os.path.join(service_folder, 'json')
        os.makedirs(json_folder)
                
        arcpy.CreateFileGDB_management(service_folder, gdb_name, 'CURRENT')
        
        params = dict(token=self.token['token'],
                     f='json')
        params_query = dict(token=self.token['token'],
                            f='json',
                            outFields='*',
                            where='1=1')
        
        url = self.services + '/{}/arcgis/rest/services/{}/FeatureServer'.format(org_id, name)

        item = self.make_request(url, params)

        for layer in item['layers']:
            layer_item_url = self.services + '/{}/arcgis/rest/services/{}/FeatureServer/{}/query'.format(org_id, name, layer['id'])
            layer_item = self.make_request(layer_item_url, params_query)

            if 'error' in layer_item:
                raise Exception(items['error']['message'], items['error']['details'])
            else:                
                json_source = os.path.join(json_folder, layer['name'] + ".json")
                
                with open(json_source, 'w') as fp:
                    json_file = json.dump(obj=layer_item, fp=fp, indent=2)

                feature_class_name = ''.join(e for e in layer['name'] if e.isalnum())
                output = os.path.join(service_folder, gdb_name, feature_class_name)
                arcpy.JSONToFeatures_conversion(json_source, output)
        return 

    def export_features_bulk(self, org_id, content, export_loc):
        """Exports all feature layers from ArcGIS Online and saves them in a File Geodatabase"""
        
        items = content['items']
        
        for i in items:
            if i['type'] == "Feature Service" and "Hosted Service" in i['typeKeywords']:
                arcpy.AddMessage("\nSaving " + i['title'])
                arcpy.AddMessage("URL: " + i['url'])
                
                service = ''.join(e for e in i['title'] if e.isalnum())
                service_folder = os.path.join(export_loc, service)
                os.makedirs(service_folder)

                json_folder = os.path.join(service_folder, 'json')
                os.makedirs(json_folder)
                
                gdb_name = 'export_' + service + '.gdb'
                
                arcpy.CreateFileGDB_management(service_folder, gdb_name, 'CURRENT')

                params = dict(token=self.token['token'],
                              f='json')
                params_query = dict(token=self.token['token'],
                                    f='json',
                                    outFields='*',
                                    where='1=1')
                
                actual_name = i['url'].split("/")[-2]
                url = self.services + '/{}/arcgis/rest/services/{}/FeatureServer'.format(org_id, actual_name)
                item = self.make_request(url, params)

                for layer in item['layers']:
                    layer_item_url = self.services + '/{}/arcgis/rest/services/{}/FeatureServer/{}/query'.format(org_id, actual_name, layer['id'])
                    layer_item = self.make_request(layer_item_url, params_query)

                    if 'error' in layer_item:
                        raise Exception(items['error']['message'], items['error']['details'])
                        pass
                    else:                    
                        json_source = os.path.join(json_folder, layer['name'] + ".json")                        
                        with open(json_source, 'w') as fp:
                            json_file = json.dump(obj=layer_item, fp=fp, indent=2)

                        feature_class_name = ''.join(e for e in layer['name'] if e.isalnum())
                        output = os.path.join(service_folder, gdb_name, feature_class_name)
                        arcpy.JSONToFeatures_conversion(json_source, output)
        return

                    
    def file_writer(self, data, location):
        with open(os.path.join(location, "itemdata-" + timestamp + ".json"), 'w') as fp:
            json.dump(obj=data, fp=fp, indent=2)
        return

def main():
    
    save_location = arcpy.GetParameterAsText(0)
    username = arcpy.GetParameterAsText(1)
    password = arcpy.GetParameterAsText(2)
    batch = arcpy.GetParameterAsText(3)

    agol = AGOL(username, password)
    
    org_id = agol.get_user()['orgId']

    backup_location = os.path.join(save_location, 'backup')
    if not os.path.exists(backup_location):
        os.makedirs(backup_location)
    session_location = os.path.join(save_location, 'backup', timestamp)
    os.makedirs(session_location)
    
    content = agol.get_user_content()
    agol.file_writer(content, session_location)

    if not batch:
        arcpy.AddMessage("\nBACKUP FEATURE LAYERS")
        arcpy.AddMessage("=====================")
        agol.export_features_bulk(org_id, agol.get_user_content(), session_location)
    else:
        arcpy.AddMessage("\nEXPORT SINGLE FEATURES")
        arcpy.AddMessage("======================")
        export = agol.export_features_single(org_id, arcpy.GetParameterAsText(4), session_location)    

    arcpy.AddMessage("\nfinished")
    print "FINISHED"


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        for error in e:
            print error
            arcpy.AddError(error)
