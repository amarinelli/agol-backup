# -*- coding: utf-8 -*-

import time
import json
import os

import tortilla
import arcpy

timestamp = time.strftime("%Y-%m-%d-%H%M%S")

class AGOL:
    """ A class for administering an ArcGIS Online account"""

    def __init__(self, in_username, in_password, expiration=60):
        self.agol = tortilla.wrap('https://www.arcgis.com')
        self.services = tortilla.wrap('https://services.arcgis.com')
        self.username = in_username
        self.password = in_password
        self.expiration = expiration
        self.token = self.gen_token()

    def gen_token(self):
        """ Returns a token given a username and password """

        param = dict(username=self.username, password=self.password, expiration=self.expiration, client='referer',
                     referer='https://www.arcgis.com', f='json')

        token = self.agol.sharing.rest.generateToken.post(params=param)
        # print token.token

        if hasattr(token, 'error'):
            arcpy.AddMessage(token.error.message)
            arcpy.AddMessage(token.error.details)
            quit()
        else:
            return token

    def get_user(self):
        """Returns personal details of the user, such as e-mail and groups,
        are returned only to the user or the administrator of the user's organization"""
        
        param = dict(token=self.token.token, f='json')

        user = self.agol.sharing.rest.community.users(self.username).get(params=param)

        if hasattr(user, 'error'):
            arcpy.AddMessage(user.error.message)
            arcpy.AddMessage(user.error.details)
            quit()
        else:
            return user
        

    def get_user_content(self):
        """ Returns the content items for a particular user """

        param = dict(token=self.token.token, f='json')

        items = self.agol.sharing.rest.content.users(self.username).get(params=param)

        if hasattr(items, 'error'):
            arcpy.AddMessage(items.error.message)
            arcpy.AddMessage(items.error.details)
            quit()
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
        
        param = dict(token=self.token.token, f='json')
        param_query = dict(token=self.token.token, f='json', outFields='*', where='1=1')
        
        item = self.services(org_id).arcgis.rest.services(name).FeatureServer.get(params=param)

        for layer in item.layers:
            layer_item = self.services(org_id).arcgis.rest.services(name).FeatureServer(layer.id).query.get(params=param_query)

            if hasattr(layer_item, 'error'):
                arcpy.AddMessage(layer_item.error.message)
                arcpy.AddMessage(layer_item.error.details)
                quit()
            else:                
                json_source = os.path.join(json_folder, layer.name + ".json")
                
                with open(json_source, 'w') as fp:
                    json_file = json.dump(obj=layer_item, fp=fp)

                feature_class_name = ''.join(e for e in layer.name if e.isalnum())
                output = os.path.join(service_folder, gdb_name, feature_class_name)
                arcpy.JSONToFeatures_conversion(json_source, output)
        return 

    def export_features_bulk(self, org_id, content, export_loc):
        """Exports all feature layers from ArcGIS Online and saves them in a File Geodatabase"""
        
        items = content.items
        
        for i in items:
            if i.type == "Feature Service" and "Hosted Service" in i.typeKeywords:
                arcpy.AddMessage("\nSaving", i.title)
                arcpy.AddMessage("URL:", i.url)
                
                service = ''.join(e for e in i.title if e.isalnum())
                service_folder = os.path.join(export_loc, service)
                os.makedirs(service_folder)

                json_folder = os.path.join(service_folder, 'json')
                os.makedirs(json_folder)
                
                gdb_name = 'export_' + service + '.gdb'
                
                arcpy.CreateFileGDB_management(service_folder, gdb_name, 'CURRENT')

                param = dict(token=self.token.token, f='json')
                param_query = dict(token=self.token.token, f='json', outFields='*', where='1=1')
                actual_name = i.url.split("/")[-2]
                item = self.services(org_id).arcgis.rest.services(actual_name).FeatureServer.get(params=param)

                for layer in item.layers:
                    layer_item = self.services(org_id).arcgis.rest.services(actual_name).FeatureServer(layer.id).query.get(params=param_query)

                    if hasattr(layer_item, 'error'):
                        arcpy.AddMessage(layer_item.error.message)
                        arcpy.AddMessage(layer_item.error.details)
                        pass
                    else:                    
                        json_source = os.path.join(json_folder, layer.name + ".json")                        
                        with open(json_source, 'w') as fp:
                            json_file = json.dump(obj=layer_item, fp=fp)

                        feature_class_name = ''.join(e for e in layer.name if e.isalnum())
                        output = os.path.join(service_folder, gdb_name, feature_class_name)
                        arcpy.JSONToFeatures_conversion(json_source, output)
        return

                    
    def file_writer(self, data, location):
        with open(os.path.join(location, "itemdata-" + timestamp + ".json"), 'w') as fp:
            json.dump(obj=data, fp=fp, indent=4)
        return


if __name__ == "__main__":
    
    save_location = arcpy.GetParameterAsText(0)
    username = arcpy.GetParameterAsText(1)
    password = arcpy.GetParameterAsText(2)
    batch = arcpy.GetParameterAsText(3)

    agol = AGOL(username, password)

    org_id = agol.get_user().orgId

    backup_location = os.path.join(save_location, timestamp)
    os.makedirs(backup_location)
    
    content = agol.get_user_content()
    agol.file_writer(content, backup_location)

    if batch:
        arcpy.AddMessage("\nBACKUP FEATURE LAYERS")
        arcpy.AddMessage("=====================")
        agol.export_features_bulk(org_id, agol.get_user_content(), backup_location)
    else:
        arcpy.AddMessage("\nEXPORT SINGLE FEATURES")
        arcpy.AddMessage("======================")
        export = agol.export_features_single(org_id, arcpy.GetParameterAsText(4), backup_location)    

    arcpy.AddMessage("\nfinished")
