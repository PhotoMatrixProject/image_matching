import csv
import requests
import time
import os
import uuid

import classify_img_match as ct


last_request_time = 0.0

def check_time():
    '''Checks when the last request was. If it was less than 3 seconds ago, it sleeps the difference.'''
    time_constraint = 3
    current_time = time.time()
    if (current_time - last_request_time) < time_constraint:
        time.sleep(time_constraint - (current_time - last_request_time))


class Manager:
    '''The class is for input and output manipulation.'''
    def __init__(self):
        self.CSV_IMG_ID = 'item'
        self.CSV_IMG_ADDR = 'imageAddr'
        self.classificatopn_path = r'result\matching'
        self.class_tool = ct.ClassificationTool(self.classificatopn_path)
        self.img_path_to_classify = "img_to_classify.jpeg"
        self.resized_img_path_to_classify = "resized_img_to_classify.jpeg"
        self.dummy_top_dist = [('', 0.0) for _ in range(3)]
        self.create_dir('result')
        self.create_dir(self.classificatopn_path)
        self.create_class_dirs()
        self.open_result_csv()

    def create_class_dirs(self):
        classes =  ['sim', 'dif']
    
        for cl in classes:
            class_path = os.path.join(self.classificatopn_path, cl)
            self.create_dir(class_path)
        return

    def open_result_csv(self):
        '''Opens the CSV file that stores the results of the pipeline.'''
        self.csv_to_write = open(os.path.join('result', 'match_results.csv'), 'w', encoding='utf-8')
        self.fieldnames = ['item1', 'imageAddr1', 'item2', 'imageAddr2', 'class1']#, 'prob1']#, 'class2', 'prob2', 'class3', 'prob3']
        self.writer = csv.DictWriter(self.csv_to_write, fieldnames=self.fieldnames)
        self.writer.writeheader()
        return
    
    def create_csv_entry(self, item1:str, img_addr1:str, item2:str, img_addr2:str, top_dist_classes:list)->dict:
        '''Creates an ebtry to the result CSV file.'''
        return {
            'item1' : item1,
            'imageAddr1' : img_addr1,
            'item2' : item2,
            'imageAddr2' : img_addr2,
            'class1' : top_dist_classes[0],
            # 'prob1' : top_dist_classes[0][1],
        }

    def create_dir(self, dir_name:str):
        '''Creates a directory with a given name, if it does not already exist.'''
        if not os.path.exists(dir_name):
            os.mkdir(dir_name)
        return
    
    def delete_img(self):
        '''Deletes the images that were created in the process of processing the input.'''
        if os.path.exists(self.resized_img_path_to_classify):
            os.remove(self.resized_img_path_to_classify)
        if os.path.exists(self.img_path_to_classify):
            os.remove(self.img_path_to_classify)


class CSVManager(Manager):
    def __init__(self):
        super().__init__()

    def _resolve_csv_image(self, img_id: str, img_address: str) -> tuple[str | None, str | None]:
        '''Returns a local image path for a CSV row, downloading remote images when needed.'''
        if img_address.startswith('http'):
            self.create_dir('temp')
            database_img_id = img_id.split('Q')[-1]
            img_path = os.path.join('temp', f'{database_img_id}_{self.img_path_to_classify}')
            if os.path.exists(img_path):
                return img_path, img_path
            if self.save_img(img_path, img_address):
                return img_path, img_path
            return None, img_path

        return img_address, None

    def process_csv(self, csv_path:str):
        '''Processes a single input CSV file and writes pairwise results for each row against rows below it.'''
        with open(csv_path, 'r', encoding='utf-8') as csv_file:
            reader = csv.DictReader(csv_file)
            rows = list(reader)

        temp_img_paths = []
        for i in range(0, len(rows)-1):
            row1 = rows[i]
            img_id1 = row1[self.CSV_IMG_ID]
            img_address1 = row1[self.CSV_IMG_ADDR]
            img_path1, cleanup_path1 = self._resolve_csv_image(img_id1, img_address1)
            if cleanup_path1 is not None:
                temp_img_paths.append(cleanup_path1)

            if img_path1 is None:
                continue

            for j in range(i + 1, len(rows)):
                row2 = rows[j]
                img_id2 = row2[self.CSV_IMG_ID]
                img_address2 = row2[self.CSV_IMG_ADDR]
                img_path2, cleanup_path2 = self._resolve_csv_image(img_id2, img_address2)
                if cleanup_path2 is not None:
                    temp_img_paths.append(cleanup_path2)

                if img_path2 is None:
                    continue

                top_dist_classes = self.class_tool.get_classification_rank(img_path1, img_path2)
                csv_entry = self.create_csv_entry(img_id1, img_address1, img_id2, img_address2, top_dist_classes)
                self.writer.writerow(csv_entry)

        # deletes downloaded remote links
        # for temp_img_path in temp_img_paths:
        #     if os.path.exists(temp_img_path):
        #         os.remove(temp_img_path)
        return

    def work_with_csv(self, csvs:list[str]):
        '''Processes a list of input CSV files.'''
        try:
            self.open_result_csv()  
            for csv in csvs:
                print(csv)
                self.process_csv(csv)
            self.delete_img()
            self.csv_to_write.close()
            return
        except Exception as e:
            print("An error occurred...", e)
            self.csv_to_write.close()
        return
    
    def save_img_unsafe(self, url:str, img_name:str)->bool:
        '''Downloads an image from the given URL.'''
        # headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0"}
        check_time()
        time.sleep(1)
        response = requests.get(url)
        global last_request_time
        last_request_time = time.time()
        if response.ok:
            with open(img_name, "wb") as f:
                f.write(response.content)
            print(f"Downloaded image from {url} to {img_name}")
        return response.ok
        
    def save_img(self, img_name:str, url:str)->bool:
        '''Calls a function that downloads an image from the URL, in case of an error enforces timeout (60 s) and tries again.'''
        try:
            if os.path.exists(img_name):
                return True
            response_ok = self.save_img_unsafe(url, img_name)
            return response_ok
        except Exception as e:
            print("Error occurred. The error is ", e)
            print("Let me try again...")
            time.sleep(60)
            response_ok = self.save_img_unsafe(url, img_name)
            return response_ok


class DIRManager(Manager):
    def __init__(self):
        super().__init__()
    

    def process_dir(self, dir_name:str):
        '''Processes a single directory, that contains images (PNG, JPEG, JPG), and writes the results to the output CSV file. 
        Ignores everything except for images.'''
        imgs = os.listdir(dir_name)
        for i in range(len(imgs)):
            img_path1 = os.path.join(dir_name, imgs[i])
            for j in range(i+1, len(imgs)):
                img_path2 = os.path.join(dir_name, imgs[j])
                if (img_path1.lower().endswith(('.png', '.jpg', '.jpeg')) and img_path2.lower().endswith(('.png', '.jpg', '.jpeg'))):
                    print(imgs[i], imgs[j])
                    img_id1 = imgs[i]
                    img_address1 = img_path1
                    img_id2 = imgs[j]
                    img_address2 = img_path2

                    top_dist_classes = self.class_tool.get_classification_rank(img_address1, img_address2)
                    csv_entry = self.create_csv_entry(img_id1, img_address1, img_id2, img_address2, top_dist_classes)
                    self.writer.writerow(csv_entry)
                else:
                    print(f'Ignoring {img_path1} and {img_path2}. Not images.')
        return


    def work_with_dir(self, dir_path:str):
        '''Expects a directory which contains directories which contain images. 
        Calls a function that processes a single directory for each directory. Ignores everything except for directories.'''
        # try:
            # self.open_result_csv(os.path.basename(dir_path))
        self.open_result_csv()
        dirs = os.listdir(dir_path)
        for d in dirs:
            d_path = os.path.join(dir_path, d)
            print(d_path)
            if os.path.isdir(d_path):
                print(d_path)
                self.process_dir(d_path)
            else:
                print(f'Ignoring {d_path}. Not a directory.')
        self.delete_img()
        self.csv_to_write.close()
        # except Exception as e:
        #     print("An error occurred...", e)
        #     self.csv_to_write.close()
        return