
const getData_Server1 = () =>{
  fetch('https://www.googleapis.com/youtube/v3/search?part=snippet&channelId=UCwNsZ7DTlA8vhhqqCmwG-aw&eventType=live&type=video&key=AIzaSyCbNWFZfJILsnNoWFSXOkZogk2Yar_1-WA')
    .then(response => {
      return response.json();
    })
  .then(responseData => {
          let videoId = "";
          let liveUrl = "";
          console.log("response Data: ", responseData)
          if(responseData.error)
          {
            videoId = '_1uWeph1zEE';
          } else {
            videoId = responseData.items[0].id.videoId;
          }
          liveUrl = 'https://www.youtube.com/watch?v='+videoId;
          window.open(liveUrl);
        }).catch(err => {
          console.log("Error: ", err)
        })
};

const getData_Server2 = () =>{
  fetch('https://www.googleapis.com/youtube/v3/search?part=snippet&channelId=UCwNsZ7DTlA8vhhqqCmwG-aw&eventType=live&type=video&key=AIzaSyC1At80HIfIDT4kh95LfSPJSle7jxRtTpw')
    .then( (response) => {
      return response.json()
    })
    .then(responseData => {
      let videoId = "";
      let liveUrl = "";
      if(responseData.error)
      {
        videoId='_1uWeph1zEE';
      } else {
        videoId = responseData.items[0].id.videoId
      }
        liveUrl = 'https://www.youtube.com/watch?v='+videoId;
        window.open(liveUrl);
        return liveUrl
    }).catch(err=>{
      console.log("Error", err)
    });
};
