
# 🎙️ Narrator-extension![Narrator](https://github.com/user-attachments/assets/f28ed7f3-15b8-491e-9640-557dfabac68b)


This is an extension that reads text from any tab with lifelike, expressive voices. It’s like having your own personal narrator, perfect for hands-free reading or giving your eyes a break.



https://github.com/user-attachments/assets/169993ef-92a1-4f5f-b01c-ba6a5c955391


## 📋 Installation

To install this app, first clone this repository. It’s recommended _(but optional)_ to create a virtual environment for this project:

```
conda create --name narrator python=3.9
```

Then activate the environment

```
conda activate narrator
```
Install CUDA (_To enabledspeech streaming_)

```
 pip install torch==2.2.2+cu118 -f https://download.pytorch.org/whl/torch_stable.html
```
Finally install the project requiremets _(make sure to run this command inside the repo directory )_

```
pip install -r requirements.txt
```

You also need `ffmpeg` installed:

```
conda install -c conda-forge ffmpeg
```

Alternatively, once you've cloned the repository, you can run the `install.bat` file on Windows or the `install.sh` file on Linux to set up everything.

## Loading the extension

1. Go to `chrome://extensions`
2. Enable Developer mode![developer mode](https://github.com/user-attachments/assets/72598162-fa60-412b-bc41-e7b17cc09c0d)

3. Load the folder `chrome_extension`

## Running the Extension

To run the extension, you first need to start the server on your machine.

_Don't forget to activate the environment first if you created one._

```
 uvicorn server:app --host 0.0.0.0 --port 5000 
```

and now you are set to use it

### Notes

- This app performs optimally using **CUDA**. While it can run on a CPU, please note that in this case, it won’t stream the text in real-time. Instead, it will process the entire text first and then play it all at once.

  To add your own voices , you  have to :

1. **Add Your Voice File**\
   Place a `.wav` file of approximately 6 seconds in the `voices` folder.
2. **Update** `model.py`\
   Add your voice to the `voices` dictionary in `model.py`. It should look like this:

   ```
   voices = { "name" : "voices/name.wav"}
   ```
3. **Update** `popup.html`\
   Add an option for your voice in the `popup.html` file. Ensure the `value` matches the `"name"` used in `model.py`:

   ```html
   <option value="name">name</option>
   ```
4. **Refresh the Extension**\
   Go to `chrome://extensions` and refresh your extension to see the new voice option.![refresh](https://github.com/user-attachments/assets/eb99705a-27cc-4448-bd08-a555d32a7b61)

