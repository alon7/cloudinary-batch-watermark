import cloudinary
import cloudinary.uploader
import cloudinary.api
import os
from PIL import Image
import argparse
import configparser

def get_main_color(image_path):
    """
    Return an rgb tuple
    :param file: Image path
    :return: rgb tuple containing the most significant
    color in the south east corner of the image
    """
    # Use Pillow library to load the image as an object
    img = Image.open(image_path)
    width = img.size[0]
    height = img.size[1]
    # Crop the south east corner of the image
    img_cropped = img.crop(
        (
            width - 200,
            height - 150,
            width,
            height
        )
    )
    colors = img_cropped.getcolors(1024000)
    max_occurence, most_present = 0, 0
    try:
        for c in colors:
            if c[0] > max_occurence:
                (max_occurence, most_present) = c
        return most_present
    except TypeError:
        raise Exception("Too many colors in the image")

def get_watermark_color(image_path):
    # Get main color from the corner of the image
    main_color = get_main_color(image_path)
    # Calculate the gamma color of the image to understand it it's closer to white or black
    Y = 0.2126 * main_color[0] + 0.7152 * main_color[1] + 0.0722 * main_color[2]
    # Kinda confusing, if the number is less than 128, it is more closer to black,
    # Therefore, we want the white watermark and we return white. If it's closer to to white,
    # We want to return a black watermark
    return 'white' if Y < 128 else 'black'

def download_transformed_image(output_folder, output_file, cloudinary_upload):
    """

    :param output_folder: Output folder to download the image to
    :param output_file: Output filename to name the downloaded image
    :param cloudinary_upload: cloudinary upload response (pull the transformed image url from it)
    :return: True on success, False on Failure
    """
    output_path = os.path.join(output_folder, output_file)
    print('Downloading transformed image to: %s' % output_path)

def iterate_images(input_directory, output_directory,
                   black_watermark_transformation, white_watermark_transformation,
                   download=False):
    for root, subdirs, files in os.walk(input_directory):
        if len(files) < 0:
            # No files in this directory
            continue
        if root is not input_directory and download:
            # Create a duplicate directory on the output folder if we want to download the images at the end
            output_duplicate = root.replace(input_directory, output_directory) + ' + Resized + Watermarked'
            os.makedirs(output_duplicate, exist_ok=True)
        for f in files:
            if f.lower().endswith('.jpg') or f.lower().endswith('.png'):
                image_path = os.path.join(root, f)
                print('Analyzing east south watermark color for image: %s' % image_path)
                watermark_color = get_watermark_color(image_path)
                print('Watermark color: %s' % watermark_color)
                cloudinary_upload = None
                if watermark_color is 'black':
                    # Assign black watermark transformation
                    print('Upload to cloudinary with transformation: %s' % black_watermark_transformation)
                    cloudinary_upload = cloudinary.uploader.upload(image_path, transformation=[black_watermark_transformation])
                elif watermark_color is 'white':
                    # Assign white watermark transformation
                    print('Upload to cloudinary with transformation: %s' % white_watermark_transformation)
                    cloudinary_upload = cloudinary.uploader.upload(image_path, transformation=[white_watermark_transformation])

                if download:
                    # If download flag, download the transformed image
                    download_transformed_image(output_duplicate, f, cloudinary_upload)


def main():
    args = parse_arguments()
    config = parse_config(args.config)
    cloudinary.config(
        cloud_name=config.get('cloudinary', 'cloud_name'),
        api_key=config.get('cloudinary', 'api_key'),
        api_secret=config.get('cloudinary', 'api_secret')
    )
    input_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), config.get('script', 'input_folder'))
    output_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), config.get('script', 'output_folder'))

    print('Input folder: %s' % input_folder)
    print('Output folder: %s' % output_folder)

    black_watermark_transformation = config.get('script', 'black_watermark_transformation')
    white_watermark_transformation = config.get('script', 'white_watermark_transformation')

    try:
        iterate_images(input_folder, output_folder,
                   black_watermark_transformation,
                   white_watermark_transformation, download=args.download)
    except cloudinary.api.Error:
        print('ERROR while uploading to cloudinary, probably connectivity issues')
    # for root, subdirs, files in os.walk(DIR_NAME):
    #     if len(files) < 0:
    #         continue
    #     # Create a duplicate directory
    #     new_dir = root.replace(DIR_NAME, OUTPUT_DIR_NAME)
    #     os.makedirs(new_dir, exist_ok=True)
    #
    #     for f in files:
    #         if f.lower().endswith('.jpg') or f.lower().endswith('png'):
    #             image_path = os.path.join(root, f)
    #             print('uploading: ' + image_path)
    #             watermark_color = get_watermark_color(image_path)
    #             if watermark_color is 'black':
    #                 print('Black watermark added')
    #                 c = cloudinary.uploader.upload(image_path, transformation=["ciaboga_transformation_black"])
    #                 print(c)
    #             elif watermark_color is 'white':
    #                 print('White watermark added')
    #                 c = cloudinary.uploader.upload(image_path, transformation=["ciaboga_transformation_white"])
    #                 print(c)

def parse_arguments():
    """
    Declare program arguments and handle parsing
    :return: ArgumentParser object or exit if arguments not satisfied
    """
    parser = argparse.ArgumentParser(description='Iterate through images, decide if the watermark should be white or'
                                                 ' black and upload the image to cloudinary cloud with the correct transformation.'
                                                 ' Supports .jpg and .png images')
    parser.add_argument('config', help='Path to configuration file')
    parser.add_argument('-d', '--download', action='store_true', help='Download the created photos locally')
    return parser.parse_args()

def parse_config(config_path):
    """
    Parse configuration file and check if it is valid
    :param config_path: the path to the configuration file
    :return: ConfigParser object or exit if configuration is invalid
    """
    if not os.path.exists(config_path):
        print('Configuration file was not found at the path: %s' % config_path)
        exit(-1)

    config = configparser.ConfigParser()
    config.read(config_path)
    # Cloudinary section
    if not 'cloudinary' in config:
        print('cloudinary section [cloudinary] is missing from configuration file. Please look at README.md')
        exit(-1)
    if not config.has_option('cloudinary', 'cloud_name'):
        print('cloud_name option is missing from configuration file. Please look at README.md')
        exit(-1)
    if not config.has_option('cloudinary', 'api_key'):
        print('api_key option is missing from configuration file. Please look at README.md')
        exit(-1)
    if not config.has_option('cloudinary', 'api_secret'):
        print('api_secret option is missing from configuration file. Please look at README.md')
        exit(-1)

    # Script section
    if not 'script' in config:
        print('script section [script] is missing from configuration file. Please look at README.md')
        exit(-1)
    if not config.has_option('script', 'input_folder'):
        print('input_folder option is missing from configuration file. Please look at README.md')
        exit(-1)
    if not config.has_option('script', 'output_folder'):
        print('output_folder option is missing from configuration file. Please look at README.md')
        exit(-1)
    if not config.has_option('script', 'black_watermark_transformation'):
        print('black_watermark_transformation option is missing from configuration file. Please look at README.md')
        exit(-1)
    if not config.has_option('script', 'white_watermark_transformation'):
        print('white_watermark_transformation option is missing from configuration file. Please look at README.md')
        exit(-1)

    return config


if __name__ == '__main__':
    main()